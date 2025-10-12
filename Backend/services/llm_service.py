"""
LLM服务 (基于LangChain框架)
提供大语言模型集成、问答生成、流式输出等功能
使用 LangChain Ollama 集成
"""

import json
import time
import requests
from typing import List, Dict, Any, Optional, Generator, Tuple
from flask import current_app, stream_template
import logging

# LangChain imports
from langchain_ollama import OllamaLLM as LangChainOllama
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler

logger = logging.getLogger(__name__)


class LLMService:
    """LLM服务类 (基于LangChain)"""
    
    def __init__(self):
        """初始化LLM服务"""
        self.model_name = current_app.config.get('LLM_MODEL', 'qwen3:8b')
        self.ollama_host = current_app.config.get('OLLAMA_HOST', 'http://localhost:11434')
        self.llm = None  # LangChain Ollama LLM
        self.max_tokens = current_app.config.get('LLM_MAX_TOKENS', 2048)
        self.temperature = current_app.config.get('LLM_TEMPERATURE', 0.7)
        
        # ✅ 服务状态管理
        self.is_initialized = False
        self.last_health_check = None
        self.connection_retry_count = 0
        self.max_retry_count = 3
        self.retry_interval = 5  # 秒
        
        # 初始化LangChain Ollama客户端
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化LangChain Ollama客户端"""
        init_start = time.time()
        try:
            logger.info(f"🚀 开始初始化LangChain Ollama客户端，主机: {self.ollama_host}")
            
            # 创建 LangChain Ollama LLM
            self.llm = LangChainOllama(
                model=self.model_name,
                base_url=self.ollama_host,
                temperature=self.temperature,
                num_predict=self.max_tokens,
                top_p=0.9,
                top_k=40
            )
            
            logger.info(f"✅ LangChain Ollama客户端初始化成功，模型: {self.model_name}")
            
            # ✅ 生产级优化：启动时只检查连接，不发送测试请求
            # 模型可用性将在health check的deep_check或首次实际使用时验证
            self._check_connection_only()
            self.is_initialized = True
            self.connection_retry_count = 0
            
            init_time = time.time() - init_start
            logger.info(f"⏱️  LLM服务初始化完成，耗时: {init_time:.2f}秒")
            
        except Exception as e:
            init_time = time.time() - init_start
            logger.error(f"❌ LangChain Ollama客户端初始化失败 (耗时: {init_time:.2f}秒): {str(e)}")
            # 不抛出异常，允许服务继续运行
            logger.warning("⚠️  LLM服务将以降级模式运行")
            self.llm = None
            self.is_initialized = False
    
    def _check_connection_only(self):
        """
        仅检查Ollama服务连接（不发送测试请求）
        生产级优化：启动时只验证服务可达性，不实际调用模型
        """
        try:
            check_start = time.time()
            # 使用HTTP请求检查Ollama服务是否在线
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=3)
            check_time = time.time() - check_start
            
            if response.status_code == 200:
                logger.info(f"✅ Ollama服务连接正常 (耗时: {check_time:.2f}秒): {self.ollama_host}")
                # 可选：检查模型是否在列表中
                try:
                    data = response.json()
                    models = [model.get('name', '') for model in data.get('models', [])]
                    if self.model_name in models:
                        logger.info(f"✅ 模型 {self.model_name} 已安装")
                    else:
                        logger.warning(f"⚠️  模型 {self.model_name} 未在已安装列表中: {models}")
                except Exception:
                    pass
            else:
                logger.warning(f"⚠️  Ollama服务响应异常: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Ollama服务连接超时: {self.ollama_host}")
            raise
        except Exception as e:
            logger.error(f"❌ Ollama服务连接检查失败: {str(e)}")
            raise
    
    def _check_model_availability(self):
        """
        检查模型可用性（通过实际调用测试）
        仅在health check的deep_check=True时调用
        """
        try:
            check_start = time.time()
            # 使用 LangChain API 测试模型（使用短文本）
            test_response = self.llm.invoke("Hi")
            check_time = time.time() - check_start
            
            if test_response:
                logger.info(f"✅ LangChain模型 {self.model_name} 可用性测试通过 (耗时: {check_time:.2f}秒)")
            else:
                logger.warning(f"⚠️  LangChain模型 {self.model_name} 响应为空")
        except Exception as e:
            check_time = time.time() - check_start
            logger.error(f"❌ LangChain模型可用性检查失败 (耗时: {check_time:.2f}秒): {str(e)}")
            raise

    def _try_reconnect(self) -> bool:
        """尝试重新连接LLM服务"""
        try:
            logger.info(f"尝试重新连接LLM服务，主机: {self.ollama_host}")
            
            # 重新创建 LangChain Ollama LLM
            self.llm = LangChainOllama(
                model=self.model_name,
                base_url=self.ollama_host,
                temperature=self.temperature,
                num_predict=self.max_tokens,
                top_p=0.9,
                top_k=40
            )
            
            # 测试连接
            test_response = self.llm.invoke("测试")
            if test_response:
                logger.info(f"LLM服务重连成功，模型: {self.model_name}")
                self.is_initialized = True
                self.connection_retry_count = 0
                return True
            else:
                logger.warning(f"LLM服务重连后响应为空")
                return False
                
        except Exception as e:
            logger.error(f"LLM服务重连失败: {str(e)}")
            self.connection_retry_count += 1
            return False

    def ensure_connection(self) -> bool:
        """
        确保LLM服务连接可用，如果不可用则尝试重连
        生产级优化：优先使用轻量级连接检查
        """
        # 如果已经初始化且连接正常，直接返回
        if self.is_initialized and self.llm is not None:
            try:
                # ✅ 使用轻量级HTTP检查代替实际模型调用
                response = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
                if response.status_code == 200:
                    return True
            except Exception as e:
                logger.warning(f"⚠️  LLM连接测试失败，尝试重连: {str(e)}")
        
        # 如果重试次数超过限制，不再尝试
        if self.connection_retry_count >= self.max_retry_count:
            logger.warning(f"⚠️  LLM服务重连次数已达上限 ({self.max_retry_count})，停止重试")
            return False
        
        # 尝试重连
        return self._try_reconnect()
    
    def initialize_llm_model(self) -> bool:
        """初始化LLM模型"""
        try:
            if self.llm is None:
                self._initialize_client()
            
            # 使用 LangChain API 测试模型
            test_response = self.llm.invoke("你好")
            
            logger.info("LangChain LLM模型初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"LangChain LLM模型初始化失败: {str(e)}")
            return False
    
    def generate_answer(self, query: str, context: List[Dict], options: Optional[Dict] = None) -> Dict[str, Any]:
        """生成答案 (使用LangChain Ollama)"""
        try:
            start_time = time.time()
            
            logger.info(f"开始生成答案，查询长度: {len(query)}, 上下文数量: {len(context)}")
            
            # 检查LLM是否初始化
            if self.llm is None:
                logger.error("LangChain Ollama未初始化")
                return {
                    'answer': '抱歉，AI服务暂时不可用，请稍后重试。',
                    'formatted_response': '抱歉，AI服务暂时不可用，请稍后重试。',
                    'quality_score': 0.0,
                    'response_time': 0,
                    'model': self.model_name,
                    'error': 'LangChain Ollama not initialized'
                }
            
            # 构建提示词
            prompt = self.build_prompt(query, context)
            logger.info(f"提示词构建完成，长度: {len(prompt)}")
            
            logger.info(f"开始调用LangChain LLM模型: {self.model_name}")
            
            # 使用 LangChain API 调用模型生成
            answer = self.llm.invoke(prompt)
            
            logger.info(f"LangChain LLM模型响应完成，耗时: {time.time() - start_time:.2f}秒")
            
            # 处理响应
            answer = answer.strip() if isinstance(answer, str) else str(answer).strip()
            
            # 评估答案质量
            quality_score = self.evaluate_answer_quality(answer, query, context)
            
            # 格式化响应
            formatted_response = self.format_response(answer, context)
            
            return {
                'answer': answer,
                'formatted_response': formatted_response,
                'quality_score': quality_score,
                'response_time': time.time() - start_time,
                'model': self.model_name,
                'tokens_used': len(answer.split())  # 简单估算
            }
            
        except Exception as e:
            logger.error(f"LangChain生成答案失败: {str(e)}")
            return {
                'answer': '抱歉，我无法回答您的问题。',
                'formatted_response': '抱歉，我无法回答您的问题。',
                'quality_score': 0.0,
                'response_time': 0,
                'model': self.model_name,
                'error': str(e)
            }
    
    def stream_response(self, query: str, context: List[Dict], options: Optional[Dict] = None) -> Generator[str, None, None]:
        """流式输出响应 (使用LangChain Ollama)"""
        try:
            # 构建提示词
            prompt = self.build_prompt(query, context)
            
            # 使用 LangChain API 流式生成
            for chunk in self.llm.stream(prompt):
                if chunk:
                    yield str(chunk)
                    
        except Exception as e:
            logger.error(f"LangChain流式输出失败: {str(e)}")
            yield f"生成失败: {str(e)}"
    
    def evaluate_answer_quality(self, answer: str, query: str, context: List[Dict]) -> float:
        """评估答案质量"""
        try:
            if not answer or len(answer.strip()) < 10:
                return 0.0
            
            score = 0.0
            
            # 1. 长度评分 (0-20分)
            length_score = min(20, len(answer) / 10)
            score += length_score
            
            # 2. 相关性评分 (0-30分)
            # 简单的关键词匹配
            query_words = set(query.lower().split())
            answer_words = set(answer.lower().split())
            common_words = query_words.intersection(answer_words)
            relevance_score = min(30, len(common_words) * 5)
            score += relevance_score
            
            # 3. 结构化评分 (0-25分)
            # 检查是否包含结构化信息
            structure_indicators = ['。', '，', '：', '；', '1.', '2.', '3.', '首先', '其次', '最后']
            structure_count = sum(1 for indicator in structure_indicators if indicator in answer)
            structure_score = min(25, structure_count * 3)
            score += structure_score
            
            # 4. 上下文相关性 (0-25分)
            if context:
                context_text = ' '.join([doc.get('content', '') for doc in context])
                context_words = set(context_text.lower().split())
                context_overlap = len(answer_words.intersection(context_words))
                context_score = min(25, context_overlap * 2)
                score += context_score
            
            # 归一化到0-100分
            final_score = min(100, score)
            
            return final_score / 100.0  # 返回0-1之间的分数
            
        except Exception as e:
            logger.error(f"评估答案质量失败: {str(e)}")
            return 0.5  # 默认中等分数
    
    def format_response(self, answer: str, sources: List[Dict]) -> Dict[str, Any]:
        """格式化响应"""
        try:
            # 提取来源信息
            source_info = []
            for i, source in enumerate(sources[:3], 1):  # 最多显示3个来源
                source_info.append({
                    'id': source.get('id'),
                    'title': source.get('title', ''),
                    'url': source.get('source_url', ''),
                    'relevance': source.get('similarity_score', 0.0)
                })
            
            # 格式化响应
            formatted_response = {
                'answer': answer,
                'sources': source_info,
                'source_count': len(sources),
                'generated_at': time.time(),
                'model': self.model_name
            }
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"格式化响应失败: {str(e)}")
            return {
                'answer': answer,
                'sources': [],
                'source_count': 0,
                'generated_at': time.time(),
                'model': self.model_name,
                'error': str(e)
            }
    
    def build_prompt(self, query: str, context: List[Dict]) -> str:
        """构建提示词"""
        try:
            # 构建上下文
            context_text = ""
            for i, doc in enumerate(context[:5], 1):  # 最多使用5个文档
                content = doc.get('content', '') or doc.get('title', '')
                if content:
                    context_text += f"文档{i}：{content[:500]}...\n\n"
            
            # 构建提示词模板
            prompt_template = """你是一个专业的智能问答助手。请基于以下知识库内容，准确、客观地回答用户的问题。

知识库内容：
{context}

问题：{query}

请提供详细、准确的回答，并遵循以下要求：
1. 回答要准确、客观，基于提供的知识库内容
2. 如果知识库内容不足以回答问题，请明确说明
3. 回答要结构清晰，逻辑性强
4. 可以适当引用知识库内容来支持你的回答
5. 回答要简洁明了，避免冗余信息

回答："""

            prompt = prompt_template.format(
                context=context_text.strip(),
                query=query
            )
            
            return prompt
            
        except Exception as e:
            logger.error(f"构建提示词失败: {str(e)}")
            return f"请回答以下问题：{query}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        try:
            if self.client is None:
                return {'error': '客户端未初始化'}
            
            models = self.client.list()
            current_model = None
            
            for model in models['models']:
                if model['name'] == self.model_name:
                    current_model = model
                    break
            
            return {
                'model_name': self.model_name,
                'model_info': current_model,
                'available_models': [model['name'] for model in models['models']],
                'ollama_host': self.ollama_host,
                'max_tokens': self.max_tokens,
                'temperature': self.temperature
            }
            
        except Exception as e:
            logger.error(f"获取模型信息失败: {str(e)}")
            return {'error': str(e)}
    
    def health_check(self, deep_check: bool = False) -> Dict[str, Any]:
        """
        健康检查
        
        Args:
            deep_check: 是否执行深度检查（包括实际的模型调用测试），默认False
        """
        try:
            # ✅ 更新最后健康检查时间
            self.last_health_check = time.time()
            
            # ✅ 如果连接不可用，尝试重连
            if not self.is_initialized or self.llm is None:
                logger.info("LLM服务未初始化，尝试重连...")
                self.ensure_connection()
            
            status = {
                'llm_initialized': self.llm is not None,
                'is_initialized': self.is_initialized,
                'model_name': self.model_name,
                'ollama_host': self.ollama_host,
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'framework': 'LangChain',
                'retry_count': self.connection_retry_count,
                'last_health_check': self.last_health_check
            }
            
            # 测试模型响应
            if deep_check and self.llm:
                try:
                    test_response = self.llm.invoke("测试")
                    status['model_test'] = bool(test_response)
                    if test_response:
                        logger.info("LLM服务深度健康检查通过")
                except Exception as e:
                    logger.warning(f"LLM服务深度健康检查失败: {str(e)}")
                    status['model_test'] = False
                    # 尝试重连
                    if self.ensure_connection():
                        try:
                            test_response = self.llm.invoke("测试")
                            status['model_test'] = bool(test_response)
                        except:
                            status['model_test'] = False
            elif not deep_check:
                # 快速检查：验证LLM是否初始化
                status['model_test'] = self.llm is not None
            else:
                status['model_test'] = False
            
            return status
            
        except Exception as e:
            logger.error(f"LangChain LLM服务健康检查失败: {str(e)}")
            return {'error': str(e)}


# 全局LLM服务实例
llm_service = None


def get_llm_service() -> LLMService:
    """获取LLM服务实例"""
    global llm_service
    if llm_service is None:
        llm_service = LLMService()
    return llm_service
