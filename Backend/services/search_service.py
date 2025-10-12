"""
检索服务 (基于LangChain框架)
提供语义检索、结果重排、搜索建议等功能
使用 LangChain Retriever 和 CrossEncoderReranker
"""

import hashlib
import json
import time
import os
from typing import List, Dict, Any, Optional, Tuple
from flask import current_app
import logging
import numpy as np

# LangChain imports
# 注意: 离线模式环境变量已在 app.py 启动时设置
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

from .vector_service import get_vector_service
from Backend.models.knowledge import KnowledgeItem
from Backend.models.search_history import SearchHistory
from Backend.utils.response import success_response, error_response

logger = logging.getLogger(__name__)


class SearchService:
    """检索服务类 (基于LangChain)"""
    
    def __init__(self):
        """初始化检索服务"""
        init_start = time.time()
        
        self.vector_service = get_vector_service()
        self.rerank_model = None  # LangChain CrossEncoderReranker
        self.compression_retriever = None  # LangChain ContextualCompressionRetriever
        self.cache_enabled = current_app.config.get('SEARCH_CACHE_ENABLED', True)
        self.cache_ttl = current_app.config.get('SEARCH_CACHE_TTL', 3600)  # 1小时
        
        logger.info("🚀 开始初始化检索服务...")
        
        # ✅ 生产级优化：预加载重排模型，提升首次搜索性能
        self._initialize_rerank_model()
        
        init_time = time.time() - init_start
        logger.info(f"⏱️  检索服务初始化完成，耗时: {init_time:.2f}秒")
    
    def _initialize_rerank_model(self):
        """初始化重排模型 (使用官方离线模式)"""
        rerank_start = time.time()
        try:
            rerank_model_name = current_app.config.get('RERANK_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
            cache_dir = current_app.config.get('MODEL_CACHE_DIR', os.path.expanduser('~/.cache/huggingface/hub'))
            
            # 确保缓存目录存在
            os.makedirs(cache_dir, exist_ok=True)
            
            logger.info(f"📦 开始加载重排模型: {rerank_model_name}")
            
            # 创建 LangChain HuggingFaceCrossEncoder，使用官方离线配置
            # 注意: 使用 cache_folder 参数（官方推荐）
            cross_encoder = HuggingFaceCrossEncoder(
                model_name=rerank_model_name,
                model_kwargs={
                    'device': 'cpu',
                    'local_files_only': True,  # 强制使用本地文件
                    'trust_remote_code': False,
                    'cache_folder': cache_dir  # 使用 cache_folder 而不是 cache_dir
                }
            )
            
            # 创建 LangChain CrossEncoderReranker
            self.rerank_model = CrossEncoderReranker(
                model=cross_encoder,
                top_n=5  # 默认返回前5个结果
            )
            
            rerank_time = time.time() - rerank_start
            logger.info(f"✅ LangChain重排模型 {rerank_model_name} 加载成功 (耗时: {rerank_time:.2f}秒, 离线模式)")
        except Exception as e:
            rerank_time = time.time() - rerank_start
            logger.error(f"❌ LangChain重排模型加载失败 (耗时: {rerank_time:.2f}秒): {str(e)}")
            logger.warning("⚠️  重排功能将不可用，但基本检索功能仍可正常工作")
            # 重排模型加载失败不影响基本检索功能
    
    def semantic_search(self, query: str, top_k: int = 20, filters: Optional[Dict] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """语义检索"""
        try:
            start_time = time.time()
            
            # 检查缓存
            if self.cache_enabled:
                cached_result = self._get_cached_result(query, top_k, filters)
                if cached_result:
                    logger.info(f"命中缓存，查询: {query}")
                    return cached_result
            
            # 向量服务可用性检查
            vectors_available = False
            try:
                vectors_available = (
                    self.vector_service is not None and
                    getattr(self.vector_service, 'embedding_model', None) is not None and
                    getattr(self.vector_service, 'faiss_index', None) is not None and
                    len(getattr(self.vector_service, 'id_mapping', {}) or {}) > 0
                )
            except Exception:
                vectors_available = False
            
            results: List[Dict[str, Any]] = []
            search_type = 'semantic'
            response_time = 0.0
            
            if vectors_available:
                # 生成查询向量
                query_vector = self.vector_service.vectorize_text(query)
                
                # 执行向量搜索
                scores, knowledge_ids = self.vector_service.search_similar(query_vector, top_k)
                
                # 获取文档详情
                documents = self._get_documents_by_ids(knowledge_ids, filters)
                
                # 构建结果
                for i, (doc, score) in enumerate(zip(documents, scores)):
                    if doc:  # 确保文档存在
                        results.append({
                            'id': doc.id,
                            'title': doc.title,
                            'content': doc.content[:500] + '...' if len(doc.content) > 500 else doc.content,
                            'summary': doc.summary,
                            'source_url': doc.source_url,
                            'source_type': doc.source_type,
                            'category': doc.category,
                            'tags': doc.tags,
                            'published_at': doc.published_at.isoformat() if doc.published_at else None,
                            'created_at': doc.created_at.isoformat(),
                            'similarity_score': float(score),
                            'rank': i + 1
                        })
                response_time = time.time() - start_time
            
            # 当无向量可用或无语义结果时，回退到关键词检索
            if not vectors_available or not results:
                keyword_results = self._keyword_search(query, filters, top_k)
                # 关键词结果也要记录 rank
                for i, r in enumerate(keyword_results):
                    r['rank'] = i + 1
                results = keyword_results
                search_type = 'keyword' if not vectors_available else 'semantic_fallback_keyword'
                response_time = time.time() - start_time
            
            # 记录搜索历史（需要传入user_id）
            self._record_search_history(query, len(results), time.time() - start_time, user_id)
            
            # 缓存结果
            if self.cache_enabled:
                self._cache_result(query, top_k, filters, results)
            
            return {
                'query': query,
                'results': results,
                'total': len(results),
                'response_time': response_time,
                'search_type': search_type
            }
            
        except Exception as e:
            # 语义检索链路异常时，降级到关键词检索，避免整体返回空
            logger.error(f"语义检索失败，自动回退关键词检索: {str(e)}")
            try:
                fallback_results = self._keyword_search(query, filters, top_k)
                for i, r in enumerate(fallback_results):
                    r['rank'] = i + 1
                return {
                    'query': query,
                    'results': fallback_results,
                    'total': len(fallback_results),
                    'response_time': 0,
                    'search_type': 'keyword_fallback',
                    'error': str(e)
                }
            except Exception as fe:
                logger.error(f"关键词回退失败: {str(fe)}")
                # 最后兜底返回空结构，避免上层收到 Flask 响应元组
                return {
                    'query': query,
                    'results': [],
                    'total': 0,
                    'response_time': 0,
                    'search_type': 'error',
                    'error': f'{e}'
                }
    
    def rerank_results(self, query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
        """检索结果重排 (使用LangChain CrossEncoderReranker)"""
        try:
            if not self.rerank_model or not results:
                return results[:top_k]
            
            # 将结果转换为 LangChain Document 格式
            from langchain.docstore.document import Document
            documents = []
            for result in results:
                content = result.get('content', '') or result.get('title', '')
                metadata = {
                    'id': result.get('id'),
                    'title': result.get('title', ''),
                    'source_url': result.get('source_url', ''),
                    'similarity_score': result.get('similarity_score', 0.0)
                }
                documents.append(Document(page_content=content, metadata=metadata))
            
            # 使用 LangChain CrossEncoderReranker 进行重排
            # 更新 top_n 参数
            self.rerank_model.top_n = top_k
            reranked_docs = self.rerank_model.compress_documents(documents, query)
            
            # 将 LangChain Document 转换回字典格式
            reranked_results = []
            for i, doc in enumerate(reranked_docs):
                # 从原始results中找到对应的完整信息
                doc_id = doc.metadata.get('id')
                original_result = next((r for r in results if r.get('id') == doc_id), None)
                
                if original_result:
                    result_dict = original_result.copy()
                    result_dict['rerank_score'] = doc.metadata.get('relevance_score', 1.0 - i * 0.1)
                    result_dict['rank'] = i + 1
                    reranked_results.append(result_dict)
            
            return reranked_results[:top_k]
            
        except Exception as e:
            logger.error(f"LangChain结果重排失败: {str(e)}")
            return results[:top_k]  # 返回原始结果
    
    def hybrid_search(self, query: str, filters: Optional[Dict] = None, top_k: int = 20, user_id: Optional[int] = None) -> Dict[str, Any]:
        """混合搜索（语义搜索 + 关键词搜索）"""
        try:
            start_time = time.time()
            
            # 1. 语义搜索
            semantic_results = self.semantic_search(query, top_k, filters, user_id)
            if 'results' not in semantic_results:
                return semantic_results
            
            # 2. 关键词搜索（简单实现）
            keyword_results = self._keyword_search(query, filters, top_k)
            
            # 3. 合并和去重
            combined_results = self._merge_search_results(
                semantic_results['results'], 
                keyword_results, 
                top_k
            )
            
            # 4. 重排
            reranked_results = self.rerank_results(query, combined_results, top_k)
            
            return {
                'query': query,
                'results': reranked_results,
                'total': len(reranked_results),
                'response_time': time.time() - start_time,
                'search_type': 'hybrid'
            }
            
        except Exception as e:
            logger.error(f"混合搜索失败: {str(e)}")
            return error_response(f"混合搜索失败: {str(e)}")
    
    def web_fallback_search(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """联网搜索补充（当本地搜索无结果时）- 使用百度搜索API"""
        import requests
        from bs4 import BeautifulSoup
        import time
        
        try:
            start_time = time.time()
            logger.info(f"开始联网搜索（百度）: {query}")
            
            # 构建百度搜索URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            params = {
                'wd': query,
                'rn': top_k * 2,  # 请求更多结果以备筛选
                'ie': 'utf-8'
            }
            
            # 发送搜索请求
            logger.info(f"发送百度搜索请求: https://www.baidu.com/s?wd={query}")
            response = requests.get(
                'https://www.baidu.com/s',
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            logger.info(f"百度搜索响应状态码: {response.status_code}")
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取搜索结果 - 尝试多种选择器
            results = []
            
            # 尝试多种百度搜索结果的class名称
            result_items = soup.find_all('div', class_='result')
            if not result_items:
                result_items = soup.find_all('div', class_='c-container')
            if not result_items:
                result_items = soup.find_all('div', attrs={'id': lambda x: x and x.isdigit()})
            
            logger.info(f"找到 {len(result_items)} 个搜索结果容器")
            
            result_items = result_items[:top_k]
            
            for i, item in enumerate(result_items):
                try:
                    # 提取标题 - 尝试多种选择器
                    title_elem = item.find('h3')
                    if not title_elem:
                        title_elem = item.find('a')
                    title = title_elem.get_text(strip=True) if title_elem else '未知标题'
                    
                    # 提取链接
                    link_elem = item.find('a')
                    link = link_elem.get('href', '') if link_elem else ''
                    
                    # 提取摘要 - 尝试多种选择器
                    abstract_elem = item.find('div', class_='c-abstract')
                    if not abstract_elem:
                        abstract_elem = item.find('span', class_='content-right_8Zs40')
                    if not abstract_elem:
                        abstract_elem = item.find('div', class_='c-span-last')
                    if not abstract_elem:
                        # 尝试获取所有文本
                        abstract = item.get_text(strip=True)
                    else:
                        abstract = abstract_elem.get_text(strip=True)
                    
                    logger.info(f"解析结果 {i+1}: 标题={title[:30]}..., 摘要长度={len(abstract)}")
                    
                    # 降低要求：只要有标题就添加
                    if title and title != '未知标题':
                        # 如果没有摘要，使用标题作为内容
                        if not abstract:
                            abstract = title
                        
                        results.append({
                            'id': f'web_{i+1}',
                            'title': title,
                            'content': abstract,
                            'summary': abstract[:100] + '...' if len(abstract) > 100 else abstract,
                            'source_url': link,
                            'source_name': '百度搜索',
                            'source_type': 'web_search',
                            'score': 1.0 - (i * 0.1),  # 递减的相关性分数
                            'rank': i + 1
                        })
                        logger.info(f"成功添加搜索结果 {i+1}")
                except Exception as e:
                    logger.error(f"解析第{i+1}个搜索结果失败: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
            
            response_time = time.time() - start_time
            
            logger.info(f"联网搜索完成，找到 {len(results)} 条结果，耗时 {response_time:.2f}s")
            
            return {
                'query': query,
                'results': results,
                'total': len(results),
                'response_time': response_time,
                'search_type': 'web_fallback',
                'source': 'baidu',
                'message': f'从百度搜索获取到 {len(results)} 条结果'
            }
            
        except requests.RequestException as e:
            logger.error(f"联网搜索请求失败: {str(e)}")
            return {
                'query': query,
                'results': [],
                'total': 0,
                'response_time': 0,
                'search_type': 'web_fallback',
                'error': f'网络请求失败: {str(e)}',
                'message': '联网搜索失败，请检查网络连接'
            }
        except Exception as e:
            logger.error(f"联网搜索失败: {str(e)}")
            return {
                'query': query,
                'results': [],
                'total': 0,
                'response_time': 0,
                'search_type': 'web_fallback',
                'error': str(e),
                'message': '联网搜索失败'
            }
    
    def cache_search_results(self, query: str, results: List[Dict], expire_time: int = 3600) -> bool:
        """缓存搜索结果"""
        try:
            if not self.cache_enabled:
                return False
            
            cache_key = self._generate_cache_key(query, None, None)
            
            # 这里可以实现Redis缓存
            # 暂时使用简单的方式
            logger.info(f"缓存搜索结果: {query}")
            
            return True
            
        except Exception as e:
            logger.error(f"缓存搜索结果失败: {str(e)}")
            return False
    
    def get_search_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """获取搜索建议"""
        try:
            if len(query.strip()) < 2:
                return []
            
            # 从搜索历史中获取建议
            suggestions = self._get_suggestions_from_history(query, limit)
            
            # 可以添加更多建议来源
            # - 热门搜索词
            # - 知识库标题
            # - 预定义词汇
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"获取搜索建议失败: {str(e)}")
            return []
    
    def _get_documents_by_ids(self, knowledge_ids: List[int], filters: Optional[Dict] = None) -> List[KnowledgeItem]:
        """根据ID获取文档详情"""
        try:
            from Backend.models import db
            from flask import current_app, has_app_context
            
            # 确保在应用上下文中
            if not has_app_context():
                logger.warning("无应用上下文，跳过文档查询")
                return []
            
            query = db.session.query(KnowledgeItem).filter(
                KnowledgeItem.id.in_(knowledge_ids)
            )
            
            # 应用过滤器
            if filters:
                if filters.get('category'):
                    query = query.filter(KnowledgeItem.category == filters['category'])
                if filters.get('source_type'):
                    query = query.filter(KnowledgeItem.source_type == filters['source_type'])
                if filters.get('date_range'):
                    start_date, end_date = filters['date_range']
                    query = query.filter(
                        KnowledgeItem.published_at.between(start_date, end_date)
                    )
            
            documents = query.all()
            
            # 按原始ID顺序排序
            doc_dict = {doc.id: doc for doc in documents}
            ordered_docs = [doc_dict.get(kid) for kid in knowledge_ids if kid in doc_dict]
            
            return ordered_docs
            
        except Exception as e:
            logger.error(f"获取文档详情失败: {str(e)}")
            return []
    
    def _keyword_search(self, query: str, filters: Optional[Dict] = None, top_k: int = 20) -> List[Dict]:
        """关键词搜索（支持简单分词，大小写不敏感）"""
        try:
            from Backend.models import db
            from flask import current_app, has_app_context
            import re
            
            # 确保在应用上下文中
            if not has_app_context():
                logger.warning("无应用上下文，跳过关键词搜索")
                return []
            
            # 基础 token 提取：英文/数字 + 连续中文
            english_tokens = re.findall(r"[A-Za-z0-9]+", query.lower())
            chinese_tokens = re.findall(r"[\u4e00-\u9fff]{1,}", query)
            tokens = [t for t in english_tokens + chinese_tokens if len(t) >= 1]
            
            # 若没有有效 token，回退用原查询
            if not tokens:
                tokens = [query]
            
            # 构造 OR 查询（ilike 忽略大小写）
            or_clauses = []
            for token in tokens:
                like = f"%{token}%"
                or_clauses.extend([
                    KnowledgeItem.title.ilike(like),
                    KnowledgeItem.content.ilike(like),
                    KnowledgeItem.summary.ilike(like)
                ])
            
            search_query = db.session.query(KnowledgeItem).filter(db.or_(*or_clauses))
            
            # 应用过滤器
            if filters:
                if filters.get('category'):
                    search_query = search_query.filter(KnowledgeItem.category == filters['category'])
                if filters.get('source_type'):
                    search_query = search_query.filter(KnowledgeItem.source_type == filters['source_type'])
            
            # 按创建时间排序
            search_query = search_query.order_by(KnowledgeItem.created_at.desc())
            
            documents = search_query.limit(top_k).all()
            
            results = []
            for i, doc in enumerate(documents):
                results.append({
                    'id': doc.id,
                    'title': doc.title,
                    'content': doc.content[:500] + '...' if len(doc.content) > 500 else doc.content,
                    'summary': doc.summary,
                    'source_url': doc.source_url,
                    'source_type': doc.source_type,
                    'category': doc.category,
                    'tags': doc.tags,
                    'published_at': doc.published_at.isoformat() if doc.published_at else None,
                    'created_at': doc.created_at.isoformat(),
                    'keyword_score': 1.0,  # 简单的关键词匹配分数
                    'rank': i + 1
                })
            
            return results
            
        except Exception as e:
            logger.error(f"关键词搜索失败: {str(e)}")
            return []
    
    def _merge_search_results(self, semantic_results: List[Dict], keyword_results: List[Dict], top_k: int) -> List[Dict]:
        """合并搜索结果"""
        try:
            # 使用字典去重，以ID为键
            merged_dict = {}
            
            # 添加语义搜索结果
            for result in semantic_results:
                merged_dict[result['id']] = result
                result['search_source'] = 'semantic'
            
            # 添加关键词搜索结果
            for result in keyword_results:
                if result['id'] in merged_dict:
                    # 如果已存在，更新分数
                    merged_dict[result['id']]['keyword_score'] = result.get('keyword_score', 0)
                    merged_dict[result['id']]['search_source'] = 'both'
                else:
                    result['search_source'] = 'keyword'
                    merged_dict[result['id']] = result
            
            # 转换为列表并按综合分数排序
            merged_results = list(merged_dict.values())
            
            # 计算综合分数
            for result in merged_results:
                semantic_score = result.get('similarity_score', 0)
                keyword_score = result.get('keyword_score', 0)
                
                # 简单的分数融合策略
                if result.get('search_source') == 'both':
                    result['combined_score'] = (semantic_score + keyword_score) / 2
                else:
                    result['combined_score'] = semantic_score if result.get('search_source') == 'semantic' else keyword_score
            
            # 按综合分数排序
            merged_results.sort(key=lambda x: x['combined_score'], reverse=True)
            
            return merged_results[:top_k]
            
        except Exception as e:
            logger.error(f"合并搜索结果失败: {str(e)}")
            return semantic_results[:top_k]
    
    def _record_search_history(self, query: str, results_count: int, response_time: float, user_id: Optional[int] = None):
        """记录搜索历史"""
        try:
            # 如果没有用户ID，跳过记录（避免数据库约束错误）
            if user_id is None:
                logger.debug("跳过搜索历史记录：用户未登录")
                return
                
            from Backend.models import db
            from flask import current_app, has_app_context
            
            # 确保在应用上下文中
            if not has_app_context():
                logger.warning("无应用上下文，跳过搜索历史记录")
                return
            
            search_history = SearchHistory(
                user_id=user_id,
                query=query,
                results_count=results_count,
                response_time=response_time
            )
            
            db.session.add(search_history)
            db.session.commit()
            logger.debug(f"搜索历史记录成功：用户 {user_id}，查询 '{query}'")
            
        except Exception as e:
            logger.error(f"记录搜索历史失败: {str(e)}")
            # 不抛出异常，避免影响搜索结果
    
    def _get_suggestions_from_history(self, query: str, limit: int) -> List[str]:
        """从搜索历史获取建议"""
        try:
            from Backend.models import db
            from flask import current_app, has_app_context
            
            # 确保在应用上下文中
            if not has_app_context():
                logger.warning("无应用上下文，跳过搜索历史建议")
                return []
            
            # 获取包含查询词的搜索历史
            suggestions = db.session.query(SearchHistory.query).filter(
                SearchHistory.query.like(f'%{query}%')
            ).distinct().limit(limit).all()
            
            return [s[0] for s in suggestions]
            
        except Exception as e:
            logger.error(f"从搜索历史获取建议失败: {str(e)}")
            return []
    
    def _generate_cache_key(self, query: str, filters: Optional[Dict], top_k: int) -> str:
        """生成缓存键"""
        cache_data = {
            'query': query,
            'filters': filters,
            'top_k': top_k
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_cached_result(self, query: str, top_k: int, filters: Optional[Dict]) -> Optional[Dict]:
        """获取缓存结果"""
        # 这里可以实现Redis缓存
        # 暂时返回None
        return None
    
    def _cache_result(self, query: str, top_k: int, filters: Optional[Dict], results: List[Dict]):
        """缓存结果"""
        # 这里可以实现Redis缓存
        pass
    
    def health_check(self, deep_check: bool = False) -> Dict[str, Any]:
        """
        健康检查
        
        Args:
            deep_check: 是否执行深度检查（包括实际的搜索测试），默认False
        """
        try:
            status = {
                'vector_service_available': self.vector_service is not None,
                'rerank_model_loaded': self.rerank_model is not None,
                'cache_enabled': self.cache_enabled,
                'cache_ttl': self.cache_ttl
            }
            
            # 测试搜索功能（可选，仅在deep_check时执行）
            if deep_check and self.vector_service:
                try:
                    test_result = self.semantic_search("测试", top_k=1)
                    status['search_test'] = 'results' in test_result
                except:
                    status['search_test'] = False
            elif not deep_check:
                # 快速检查：只验证服务可用性，不执行实际搜索
                status['search_test'] = self.vector_service is not None
            else:
                status['search_test'] = False
            
            return status
            
        except Exception as e:
            logger.error(f"搜索服务健康检查失败: {str(e)}")
            return {'error': str(e)}


# 全局检索服务实例
search_service = None


def get_search_service() -> SearchService:
    """获取检索服务实例"""
    global search_service
    if search_service is None:
        search_service = SearchService()
    return search_service
