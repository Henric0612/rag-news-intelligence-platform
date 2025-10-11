"""
向量化服务 (基于LangChain框架)
提供文本向量化、FAISS索引管理等功能
使用 LangChain HuggingFaceEmbeddings 和 FAISS VectorStore
"""

import os
import json
import numpy as np
import faiss
import time
from typing import List, Tuple, Optional, Dict, Any
from flask import current_app
import logging

# LangChain imports - 使用官方推荐的包结构
# 注意: 离线模式环境变量已在 app.py 启动时设置
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS as LangChainFAISS
from langchain.docstore.document import Document as LangChainDocument

logger = logging.getLogger(__name__)


class VectorService:
    """向量化服务类 (基于LangChain)"""
    
    def __init__(self):
        """初始化向量化服务"""
        init_start = time.time()
        
        self.embedding_model = None  # LangChain HuggingFaceEmbeddings
        self.vectorstore = None  # LangChain FAISS VectorStore
        self.faiss_index = None  # 原生FAISS索引（用于兼容性）
        self.id_mapping = {}
        data_dir = self._resolve_data_dir()
        self.index_path = os.path.join(data_dir, 'faiss', 'knowledge.index')
        self.id_mapping_path = os.path.join(data_dir, 'faiss', 'id_mapping.json')
        self.dimension = 384  # all-MiniLM-L6-v2模型输出维度
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        
        logger.info("🚀 开始初始化向量化服务...")
        
        # ✅ 生产级优化：预加载模型，确保首次请求零延迟
        self._initialize_model()
        self._initialize_index()
        
        init_time = time.time() - init_start
        logger.info(f"⏱️  向量化服务初始化完成，耗时: {init_time:.2f}秒")
    
    def _initialize_model(self):
        """初始化嵌入模型 (使用官方离线模式配置)"""
        model_start = time.time()
        try:
            model_name = self._get_config('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
            cache_dir = self._get_config('MODEL_CACHE_DIR', os.path.expanduser('~/.cache/huggingface/hub'))
            
            # 确保缓存目录存在
            os.makedirs(cache_dir, exist_ok=True)
            
            logger.info(f"📦 开始加载嵌入模型: {model_name}")
            
            # 使用官方 LangChain HuggingFaceEmbeddings 配置，添加离线参数
            self.embedding_model = HuggingFaceEmbeddings(
                model_name=model_name,
                cache_folder=cache_dir,
                model_kwargs={
                    'device': 'cpu',
                    'local_files_only': True,  # 强制使用本地文件
                    'trust_remote_code': False
                },
                encode_kwargs={'normalize_embeddings': True}
            )
            
            model_time = time.time() - model_start
            logger.info(f"✅ LangChain嵌入模型 {model_name} 加载成功 (耗时: {model_time:.2f}秒, 离线模式)")
        except Exception as e:
            model_time = time.time() - model_start
            logger.error(f"❌ LangChain嵌入模型加载失败 (耗时: {model_time:.2f}秒): {str(e)}")
            # 如果模型加载失败，尝试使用备用方案
            logger.warning("⚠️  尝试使用备用嵌入方案...")
            self._initialize_fallback_model()
    
    def _initialize_fallback_model(self):
        """初始化备用嵌入模型（使用官方sentence-transformers离线模式）"""
        try:
            from sentence_transformers import SentenceTransformer
            
            model_name = self._get_config('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
            cache_dir = self._get_config('MODEL_CACHE_DIR', os.path.expanduser('~/.cache/huggingface/hub'))
            
            # 使用官方sentence-transformers离线模式
            model = SentenceTransformer(
                model_name,
                cache_folder=cache_dir,
                device='cpu'
            )
            
            # 创建自定义嵌入包装器
            class CustomEmbeddings:
                def __init__(self, model):
                    self.model = model
                
                def embed_query(self, text: str):
                    return self.model.encode(text, normalize_embeddings=True).tolist()
                
                def embed_documents(self, texts: List[str]):
                    return self.model.encode(texts, normalize_embeddings=True).tolist()
            
            self.embedding_model = CustomEmbeddings(model)
            logger.info(f"备用嵌入模型 {model_name} 加载成功（离线模式）")
            
        except Exception as e:
            logger.error(f"备用嵌入模型加载失败: {str(e)}")
            # 最后的备用方案：使用随机向量
            logger.warning("使用随机向量作为最后备用方案...")
            self._initialize_random_embeddings()
    
    def _initialize_random_embeddings(self):
        """初始化随机向量嵌入（最后备用方案）"""
        try:
            class RandomEmbeddings:
                def __init__(self, dimension=384):
                    self.dimension = dimension
                
                def embed_query(self, text: str):
                    # 基于文本内容生成伪随机向量，保证相同输入产生相同输出
                    import hashlib
                    seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
                    np.random.seed(seed)
                    vector = np.random.normal(0, 1, self.dimension)
                    return (vector / np.linalg.norm(vector)).tolist()  # 归一化
                
                def embed_documents(self, texts: List[str]):
                    return [self.embed_query(text) for text in texts]
            
            self.embedding_model = RandomEmbeddings(self.dimension)
            logger.warning("使用随机向量嵌入（仅用于测试，不建议生产使用）")
            
        except Exception as e:
            logger.error(f"随机向量嵌入初始化失败: {str(e)}")
            raise RuntimeError("所有嵌入模型初始化方案都失败了")
    
    def _initialize_index(self):
        """初始化FAISS索引"""
        index_start = time.time()
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.id_mapping_path):
                # 加载现有索引
                self.faiss_index = faiss.read_index(self.index_path)
                with open(self.id_mapping_path, 'r', encoding='utf-8') as f:
                    self.id_mapping = json.load(f)
                index_time = time.time() - index_start
                logger.info(f"✅ FAISS索引加载成功 (耗时: {index_time:.2f}秒)，包含 {len(self.id_mapping)} 个向量")
            else:
                # 创建新索引
                self.faiss_index = faiss.IndexFlatIP(self.dimension)  # 内积相似度
                self.id_mapping = {}
                index_time = time.time() - index_start
                logger.info(f"✅ 创建新的FAISS索引 (耗时: {index_time:.2f}秒)")
        except Exception as e:
            index_time = time.time() - index_start
            logger.error(f"❌ FAISS索引初始化失败 (耗时: {index_time:.2f}秒): {str(e)}")
            raise
    
    def load_embedding_model(self) -> bool:
        """加载嵌入模型"""
        try:
            if self.embedding_model is None:
                self._initialize_model()
            return True
        except Exception as e:
            logger.error(f"加载嵌入模型失败: {str(e)}")
            return False
    
    def vectorize_text(self, text: str) -> np.ndarray:
        """单文本向量化 (使用LangChain embeddings.embed_query)"""
        try:
            if self.embedding_model is None:
                raise ValueError("嵌入模型未初始化")
            
            # 文本预处理
            processed_text = self._preprocess_text(text)
            
            # 使用 LangChain API: embed_query 用于单个查询文本
            vector = self.embedding_model.embed_query(processed_text)
            return np.array(vector)  # 转换为numpy数组
        except Exception as e:
            logger.error(f"文本向量化失败: {str(e)}")
            raise
    
    def batch_vectorize(self, texts: List[str]) -> np.ndarray:
        """批量文本向量化 (使用LangChain embeddings.embed_documents)"""
        try:
            if self.embedding_model is None:
                raise ValueError("嵌入模型未初始化")
            
            # 文本预处理
            processed_texts = [self._preprocess_text(text) for text in texts]
            
            # 使用 LangChain API: embed_documents 用于批量文档
            vectors = self.embedding_model.embed_documents(processed_texts)
            return np.array(vectors)  # 转换为numpy数组
        except Exception as e:
            logger.error(f"批量文本向量化失败: {str(e)}")
            raise
    
    def build_faiss_index(self, vectors: np.ndarray, knowledge_ids: List[int]) -> bool:
        """构建FAISS索引"""
        try:
            if vectors.shape[1] != self.dimension:
                raise ValueError(f"向量维度不匹配，期望 {self.dimension}，实际 {vectors.shape[1]}")
            
            # 创建新索引
            self.faiss_index = faiss.IndexFlatIP(self.dimension)
            
            # 添加向量
            self.faiss_index.add(vectors.astype('float32'))
            
            # 更新ID映射
            for i, knowledge_id in enumerate(knowledge_ids):
                self.id_mapping[i] = knowledge_id
            
            # 保存索引
            self.save_vector_index()
            
            logger.info(f"FAISS索引构建成功，包含 {len(knowledge_ids)} 个向量")
            return True
        except Exception as e:
            logger.error(f"构建FAISS索引失败: {str(e)}")
            return False
    
    def update_vector_index(self, new_vectors: np.ndarray, new_knowledge_ids: List[int]) -> bool:
        """更新向量索引（增量添加）"""
        try:
            if self.faiss_index is None:
                raise ValueError("FAISS索引未初始化")
            
            # 检查向量维度
            if new_vectors.shape[1] != self.dimension:
                raise ValueError(f"向量维度不匹配，期望 {self.dimension}，实际 {new_vectors.shape[1]}")
            
            # 获取当前索引大小
            current_size = len(self.id_mapping)
            
            # 添加新向量
            self.faiss_index.add(new_vectors.astype('float32'))
            
            # 更新ID映射
            for i, knowledge_id in enumerate(new_knowledge_ids):
                self.id_mapping[current_size + i] = knowledge_id
            
            # 保存索引
            self.save_vector_index()
            
            logger.info(f"向量索引更新成功，新增 {len(new_knowledge_ids)} 个向量")
            return True
        except Exception as e:
            logger.error(f"更新向量索引失败: {str(e)}")
            return False

    def clear_index(self) -> bool:
        """清空并重建空的向量索引与映射"""
        try:
            # 重置索引与映射
            self.faiss_index = faiss.IndexFlatIP(self.dimension)
            self.id_mapping = {}
            # 保存空索引
            self.save_vector_index()
            logger.info("向量索引已清空并重建")
            return True
        except Exception as e:
            logger.error(f"清空向量索引失败: {str(e)}")
            return False

    def add_document(self, knowledge_id: int, text: str) -> int:
        """为单条文本生成向量并加入索引，返回 vector_id"""
        try:
            # 确保模型加载
            self.load_embedding_model()
            if self.faiss_index is None:
                self.faiss_index = faiss.IndexFlatIP(self.dimension)

            # 生成向量
            vector = self.vectorize_text(text).astype('float32')
            vector = vector.reshape(1, -1)

            # 计算新ID：使用已存在的最大ID + 1，避免重复
            if len(self.id_mapping) > 0:
                # 获取现有映射中的最大ID
                max_vector_id = max(int(k) for k in self.id_mapping.keys())
                new_vector_id = max_vector_id + 1
            else:
                new_vector_id = 0
            
            # 添加向量到索引
            self.faiss_index.add(vector)
            self.id_mapping[new_vector_id] = knowledge_id

            # 保存索引
            self.save_vector_index()
            return new_vector_id
        except Exception as e:
            logger.error(f"添加向量文档失败: {str(e)}")
            raise

    def delete_document(self, vector_id: int) -> bool:
        """删除向量映射。IndexFlatIP 不支持物理删除，这里仅移除映射条目并保存映射。
        之后的检索如果命中该 vector_id 会被忽略。
        """
        try:
            if vector_id in self.id_mapping:
                del self.id_mapping[vector_id]
                # 仅保存映射文件
                try:
                    with open(self.id_mapping_path, 'w', encoding='utf-8') as f:
                        json.dump(self.id_mapping, f, ensure_ascii=False, indent=2)
                except Exception:
                    # 若单独保存失败，尝试整体保存
                    self.save_vector_index()
                return True
            return False
        except Exception as e:
            logger.error(f"删除向量映射失败: {str(e)}")
            return False
    
    def save_vector_index(self) -> bool:
        """保存向量索引到文件"""
        try:
            if self.faiss_index is None:
                raise ValueError("FAISS索引未初始化")
            
            # 保存FAISS索引
            faiss.write_index(self.faiss_index, self.index_path)
            
            # 保存ID映射
            with open(self.id_mapping_path, 'w', encoding='utf-8') as f:
                json.dump(self.id_mapping, f, ensure_ascii=False, indent=2)
            
            logger.info("向量索引保存成功")
            return True
        except Exception as e:
            logger.error(f"保存向量索引失败: {str(e)}")
            return False
    
    def load_vector_index(self) -> bool:
        """从文件加载向量索引"""
        try:
            if not os.path.exists(self.index_path) or not os.path.exists(self.id_mapping_path):
                logger.warning("向量索引文件不存在")
                return False
            
            # 加载FAISS索引
            self.faiss_index = faiss.read_index(self.index_path)
            
            # 加载ID映射
            with open(self.id_mapping_path, 'r', encoding='utf-8') as f:
                self.id_mapping = json.load(f)
            
            logger.info(f"向量索引加载成功，包含 {len(self.id_mapping)} 个向量")
            return True
        except Exception as e:
            logger.error(f"加载向量索引失败: {str(e)}")
            return False
    
    def search_similar(self, query_vector: np.ndarray, top_k: int = 20) -> Tuple[np.ndarray, List[int]]:
        """向量相似度搜索"""
        try:
            if self.faiss_index is None:
                raise ValueError("FAISS索引未初始化")
            
            if len(self.id_mapping) == 0:
                return np.array([]), []
            
            # 执行搜索
            scores, vector_indices = self.faiss_index.search(
                query_vector.reshape(1, -1).astype('float32'), 
                min(top_k, len(self.id_mapping))
            )
            
            # 转换为知识库ID
            # 注意：JSON加载时键是字符串，需要将整数索引转换为字符串
            knowledge_ids = [self.id_mapping.get(str(idx), -1) for idx in vector_indices[0]]
            
            return scores[0], knowledge_ids
        except Exception as e:
            logger.error(f"向量相似度搜索失败: {str(e)}")
            raise
    
    def get_index_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            return {
                'total_vectors': len(self.id_mapping),
                'dimension': self.dimension,
                'index_type': 'IndexFlatIP',
                'model_name': self._get_config('EMBEDDING_MODEL', 'all-MiniLM-L6-v2'),
                'index_path': self.index_path,
                'id_mapping_path': self.id_mapping_path
            }
        except Exception as e:
            logger.error(f"获取索引统计信息失败: {str(e)}")
            return {}
    
    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        if not text:
            return ""
        
        # 基本清理
        text = text.strip()
        
        # 移除多余的空白字符
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # 限制文本长度（避免过长的文本影响性能）
        max_length = self._get_config('MAX_TEXT_LENGTH', 512)
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    def health_check(self, deep_check: bool = False) -> Dict[str, Any]:
        """
        健康检查
        
        Args:
            deep_check: 是否执行深度检查（包括实际的向量化测试），默认False
        """
        try:
            # 基础状态检查（快速，无IO操作）
            embedding_model_loaded = self.embedding_model is not None
            faiss_index_loaded = self.faiss_index is not None
            total_vectors = len(self.id_mapping)
            index_file_exists = os.path.exists(self.index_path)
            mapping_file_exists = os.path.exists(self.id_mapping_path)
            
            # 向量化功能测试（可选，仅在deep_check时执行）
            vectorization_test = None  # None表示未测试
            if deep_check and embedding_model_loaded:
                try:
                    test_vector = self.vectorize_text("测试文本")
                    vectorization_test = len(test_vector) == self.dimension
                except Exception as e:
                    logger.warning(f"向量化测试失败: {str(e)}")
                    vectorization_test = False
            
            # 综合健康状态判断
            # 基础服务健康：模型可用 + 索引可用
            # 注意：不再依赖vectorization_test，避免每次健康检查都执行推理
            service_healthy = embedding_model_loaded and faiss_index_loaded
            
            # 数据状态：是否有可搜索的向量数据
            has_data = total_vectors > 0
            
            # 整体健康状态：服务健康 + 有数据
            is_healthy = service_healthy and has_data
            
            status = {
                'embedding_model_loaded': embedding_model_loaded,
                'faiss_index_loaded': faiss_index_loaded,
                'total_vectors': total_vectors,
                'dimension': self.dimension,
                'index_file_exists': index_file_exists,
                'mapping_file_exists': mapping_file_exists,
                'service_healthy': service_healthy,
                'has_data': has_data,
                'is_healthy': is_healthy,
                'status_message': self._get_status_message(service_healthy, has_data, total_vectors, embedding_model_loaded, faiss_index_loaded)
            }
            
            # 仅在深度检查时包含vectorization_test结果
            if deep_check:
                status['vectorization_test'] = vectorization_test
            
            return status
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return {
                'error': str(e),
                'is_healthy': False,
                'status_message': f'健康检查异常: {str(e)}'
            }
    
    def _get_status_message(self, service_healthy: bool, has_data: bool, 
                           total_vectors: int, embedding_model_loaded: bool, 
                           faiss_index_loaded: bool) -> str:
        """获取状态消息"""
        if service_healthy and has_data:
            return f"向量服务正常，包含 {total_vectors} 个向量"
        elif service_healthy and not has_data:
            return "向量服务就绪，等待知识库数据"
        elif not embedding_model_loaded:
            return "嵌入模型未加载"
        elif not faiss_index_loaded:
            return "FAISS索引未加载"
        else:
            return "向量服务异常"

    def _get_config(self, key: str, default: Any) -> Any:
        """安全获取配置值：在无应用上下文时回退到默认值"""
        try:
            return current_app.config.get(key, default)
        except Exception:
            return default

    def _resolve_data_dir(self) -> str:
        """解析数据目录：优先使用应用配置，否则使用包内 data 目录"""
        try:
            data_dir = current_app.config.get('DATA_DIR')
            if data_dir:
                return data_dir
        except Exception:
            pass
        # 回退到 Backend/data 目录
        backend_root = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(backend_root, 'data')


# 全局向量服务实例
vector_service = None


def get_vector_service() -> VectorService:
    """获取向量服务实例"""
    global vector_service
    if vector_service is None:
        vector_service = VectorService()
    return vector_service
