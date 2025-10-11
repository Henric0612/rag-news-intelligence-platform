"""
RAG流程服务 (基于LangChain框架)
提供完整的检索增强生成流程
使用 LangChain Chain/LCEL 实现 RAG 流程
"""

import time
from typing import List, Dict, Any, Optional, Generator
from flask import current_app
import logging

# LangChain imports
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from .vector_service import get_vector_service
from .search_service import get_search_service
from .llm_service import get_llm_service
from Backend.utils.response import success_response, error_response

logger = logging.getLogger(__name__)


class RAGService:
    """RAG流程服务类 (基于LangChain)"""
    
    def __init__(self):
        """初始化RAG服务"""
        self.vector_service = get_vector_service()
        self.search_service = get_search_service()
        self.llm_service = get_llm_service()
        
        # RAG配置参数
        self.default_top_k = current_app.config.get('RAG_DEFAULT_TOP_K', 20)
        self.rerank_top_k = current_app.config.get('RAG_RERANK_TOP_K', 5)
        self.max_context_length = current_app.config.get('RAG_MAX_CONTEXT_LENGTH', 4000)
        self.enable_rerank = current_app.config.get('RAG_ENABLE_RERANK', True)
        self.enable_web_fallback = current_app.config.get('RAG_ENABLE_WEB_FALLBACK', False)
        
        # LangChain RAG Chain
        self.rag_chain = None
        self._initialize_rag_chain()
    
    def _initialize_rag_chain(self):
        """初始化 LangChain RAG Chain"""
        try:
            # 创建提示词模板
            template = """你是一个专业的新闻问答助手。请基于以下新闻内容，准确、客观地回答用户的问题。

新闻内容：
{context}

问题：{question}

请提供详细、准确的回答，并遵循以下要求：
1. 回答要准确、客观，基于提供的新闻内容
2. 如果新闻内容不足以回答问题，请明确说明
3. 回答要结构清晰，逻辑性强
4. 可以适当引用新闻内容来支持你的回答
5. 回答要简洁明了，避免冗余信息

回答："""
            
            self.prompt_template = PromptTemplate(
                template=template,
                input_variables=["context", "question"]
            )
            
            logger.info("LangChain RAG提示词模板初始化成功")
            
        except Exception as e:
            logger.error(f"LangChain RAG Chain初始化失败: {str(e)}")
    
    def answer_question(self, query: str, user_id: Optional[int] = None, options: Optional[Dict] = None) -> Dict[str, Any]:
        """完整RAG流程问答 (使用LangChain LCEL)"""
        try:
            start_time = time.time()
            
            # 解析选项
            top_k = options.get('top_k', self.default_top_k) if options else self.default_top_k
            enable_rerank = options.get('enable_rerank', self.enable_rerank) if options else self.enable_rerank
            enable_web_fallback = options.get('enable_web_fallback', self.enable_web_fallback) if options else self.enable_web_fallback
            
            # 1. 向量检索
            logger.info(f"开始LangChain RAG流程，查询: {query}")
            search_results = self.search_service.semantic_search(query, top_k, None, user_id)
            
            no_knowledge = False
            web_search_used = False  # ✅ 添加独立标志追踪是否使用了联网搜索
            
            if 'results' not in search_results or not search_results['results']:
                logger.warning(f"本地搜索无结果: {query}")
                no_knowledge = True
                # 尝试联网搜索
                logger.info(f"enable_web_fallback 状态: {enable_web_fallback}")
                if enable_web_fallback:
                    logger.info(f"触发联网搜索，查询: {query}")
                    web_results = self.search_service.web_fallback_search(query)
                    logger.info(f"联网搜索返回结果数: {len(web_results.get('results', []))}")
                    if web_results.get('results'):
                        search_results = web_results
                        no_knowledge = False
                        web_search_used = True  # ✅ 标记使用了联网搜索
                        logger.info("使用联网搜索结果")
                    else:
                        logger.warning("联网搜索未返回有效结果")
                else:
                    logger.warning("联网搜索未启用 (enable_web_fallback=False)")
            
            # 2. 结果重排（可选，使用LangChain CrossEncoderReranker）
            if enable_rerank:
                logger.info("执行LangChain结果重排")
                reranked_results = self.search_service.rerank_results(
                    query, 
                    search_results['results'], 
                    self.rerank_top_k
                )
                search_results['results'] = reranked_results
            
            # 3. 构建上下文
            context = self.build_context(search_results.get('results', []))
            
            # 4. 使用 LangChain LCEL 构建 RAG Chain 并生成答案
            logger.info("使用LangChain LCEL生成答案")
            
            if self.llm_service.llm and context:
                # 构建上下文字符串
                context_str = "\n\n".join([
                    f"文档{i+1}：{doc.get('title', '')}\n{doc.get('content', '')}"
                    for i, doc in enumerate(context[:5])
                ])
                
                # 使用 LangChain LCEL 构建 RAG Chain
                rag_chain = (
                    {"context": lambda x: context_str, "question": RunnablePassthrough()}
                    | self.prompt_template
                    | self.llm_service.llm
                    | StrOutputParser()
                )
                
                # 调用 Chain 生成答案
                answer = rag_chain.invoke(query)
                
                llm_response = {
                    'answer': answer,
                    'formatted_response': answer,
                    'quality_score': self._evaluate_answer_quality(answer, query, context),
                    'response_time': time.time() - start_time,
                    'model': self.llm_service.model_name,
                    'tokens_used': len(answer.split())
                }
            else:
                # 降级到原有方式
                llm_response = self.llm_service.generate_answer(query, context, options)
            
            # 5. 响应验证
            validated_response = self.validate_response(llm_response, query, context)
            
            # 6. 构建最终响应
            final_response = {
                'query': query,
                'answer': validated_response['answer'],
                'formatted_response': validated_response['formatted_response'],
                'sources': search_results.get('results', [])[:self.rerank_top_k],
                'context_length': len(str(context)),
                'quality_score': validated_response.get('quality_score', 0.0),
                'response_time': time.time() - start_time,
                'search_time': search_results.get('response_time', 0),
                'llm_time': llm_response.get('response_time', 0),
                'total_tokens': llm_response.get('tokens_used', 0),
                'model': llm_response.get('model', 'unknown'),
                'rag_version': '2.0-LangChain',
                'knowledge_used': not web_search_used,  # ✅ 如果使用了联网搜索，则没有使用知识库
                'web_search_used': web_search_used  # ✅ 直接使用标志
            }
            
            logger.info(f"LangChain RAG流程完成，耗时: {final_response['response_time']:.2f}秒")
            return final_response
            
        except Exception as e:
            logger.error(f"LangChain RAG流程失败: {str(e)}")
            return {
                'error': str(e),
                'answer': '抱歉，当前无法回答您的问题。',
                'formatted_response': {'answer': '抱歉，当前无法回答您的问题。'},
                'sources': [],
                'knowledge_used': False,
                'web_search_used': False
            }
    
    def _evaluate_answer_quality(self, answer: str, query: str, context: List[Dict]) -> float:
        """评估答案质量（简化版）"""
        try:
            if not answer or len(answer.strip()) < 10:
                return 0.0
            
            score = 0.0
            
            # 长度评分
            length_score = min(20, len(answer) / 10)
            score += length_score
            
            # 相关性评分
            query_words = set(query.lower().split())
            answer_words = set(answer.lower().split())
            common_words = query_words.intersection(answer_words)
            relevance_score = min(30, len(common_words) * 5)
            score += relevance_score
            
            # 结构化评分
            structure_indicators = ['。', '，', '：', '；', '1.', '2.', '3.']
            structure_count = sum(1 for indicator in structure_indicators if indicator in answer)
            structure_score = min(25, structure_count * 3)
            score += structure_score
            
            # 上下文相关性
            if context:
                context_text = ' '.join([doc.get('content', '') for doc in context])
                context_words = set(context_text.lower().split())
                context_overlap = len(answer_words.intersection(context_words))
                context_score = min(25, context_overlap * 2)
                score += context_score
            
            return min(100, score) / 100.0
            
        except Exception:
            return 0.5
    
    def stream_answer(self, query: str, user_id: Optional[int] = None, options: Optional[Dict] = None) -> Generator[Dict[str, Any], None, None]:
        """流式RAG问答"""
        try:
            # 解析选项
            top_k = options.get('top_k', self.default_top_k) if options else self.default_top_k
            enable_rerank = options.get('enable_rerank', self.enable_rerank) if options else self.enable_rerank
            
            # 1. 向量检索
            search_results = self.search_service.semantic_search(query, top_k, None, user_id)
            
            if 'results' not in search_results or not search_results['results']:
                yield {'type': 'error', 'message': '未找到相关信息'}
                return
            
            # 2. 结果重排（可选）
            if enable_rerank:
                reranked_results = self.search_service.rerank_results(
                    query, 
                    search_results['results'], 
                    self.rerank_top_k
                )
                search_results['results'] = reranked_results
            
            # 3. 构建上下文
            context = self.build_context(search_results['results'])
            
            # 4. 流式生成答案
            yield {'type': 'sources', 'data': search_results['results'][:self.rerank_top_k]}
            
            for chunk in self.llm_service.stream_response(query, context, options):
                yield {'type': 'content', 'data': chunk}
            
            yield {'type': 'done', 'message': '生成完成'}
            
        except Exception as e:
            logger.error(f"流式RAG失败: {str(e)}")
            yield {'type': 'error', 'message': str(e)}
    
    def build_context(self, documents: List[Dict]) -> List[Dict]:
        """构建上下文"""
        try:
            context = []
            current_length = 0
            
            for doc in documents:
                # 计算文档长度
                doc_content = doc.get('content', '') or doc.get('title', '')
                doc_length = len(doc_content)
                
                # 检查是否超过最大长度限制
                if current_length + doc_length > self.max_context_length:
                    # 截断文档内容
                    remaining_length = self.max_context_length - current_length
                    if remaining_length > 100:  # 至少保留100字符
                        truncated_content = doc_content[:remaining_length] + '...'
                        context.append({
                            'id': doc.get('id'),
                            'title': doc.get('title', ''),
                            'content': truncated_content,
                            'source_url': doc.get('source_url', ''),
                            'similarity_score': doc.get('similarity_score', 0.0)
                        })
                    break
                
                # 添加完整文档
                context.append({
                    'id': doc.get('id'),
                    'title': doc.get('title', ''),
                    'content': doc_content,
                    'source_url': doc.get('source_url', ''),
                    'similarity_score': doc.get('similarity_score', 0.0)
                })
                
                current_length += doc_length
            
            logger.info(f"构建上下文完成，包含 {len(context)} 个文档，总长度: {current_length}")
            return context
            
        except Exception as e:
            logger.error(f"构建上下文失败: {str(e)}")
            return []
    
    def integrate_vector_search(self, query: str, top_k: int = 20, user_id: Optional[int] = None) -> List[Dict]:
        """向量检索集成"""
        try:
            search_results = self.search_service.semantic_search(query, top_k, None, user_id)
            return search_results.get('results', [])
            
        except Exception as e:
            logger.error(f"向量检索集成失败: {str(e)}")
            return []
    
    def integrate_llm_generation(self, query: str, context: List[Dict], options: Optional[Dict] = None) -> Dict[str, Any]:
        """LLM生成集成"""
        try:
            llm_response = self.llm_service.generate_answer(query, context, options)
            return llm_response
            
        except Exception as e:
            logger.error(f"LLM生成集成失败: {str(e)}")
            return {
                'answer': '抱歉，生成答案时发生错误。',
                'formatted_response': {'answer': '抱歉，生成答案时发生错误。'},
                'quality_score': 0.0,
                'response_time': 0,
                'error': str(e)
            }
    
    def validate_response(self, response: Dict[str, Any], query: str, context: List[Dict]) -> Dict[str, Any]:
        """响应验证"""
        try:
            answer = response.get('answer', '')
            
            # 基本验证
            if not answer or len(answer.strip()) < 10:
                return {
                    'answer': '抱歉，我无法回答您的问题。',
                    'formatted_response': {'answer': '抱歉，我无法回答您的问题。'},
                    'quality_score': 0.0
                }
            
            # 质量评估
            quality_score = response.get('quality_score', 0.0)
            
            # 内容过滤（可选）
            # 这里可以添加内容过滤逻辑
            
            return {
                'answer': answer,
                'formatted_response': response.get('formatted_response', {'answer': answer}),
                'quality_score': quality_score
            }
            
        except Exception as e:
            logger.error(f"响应验证失败: {str(e)}")
            return {
                'answer': '抱歉，响应验证时发生错误。',
                'formatted_response': {'answer': '抱歉，响应验证时发生错误。'},
                'quality_score': 0.0
            }
    
    def _create_empty_response(self, query: str, message: str) -> Dict[str, Any]:
        """创建空响应"""
        return {
            'query': query,
            'answer': message,
            'formatted_response': {'answer': message},
            'sources': [],
            'context_length': 0,
            'quality_score': 0.0,
            'response_time': 0,
            'search_time': 0,
            'llm_time': 0,
            'total_tokens': 0,
            'model': 'none',
            'rag_version': '1.0'
        }
    
    def get_rag_stats(self) -> Dict[str, Any]:
        """获取RAG统计信息"""
        try:
            return {
                'default_top_k': self.default_top_k,
                'rerank_top_k': self.rerank_top_k,
                'max_context_length': self.max_context_length,
                'enable_rerank': self.enable_rerank,
                'enable_web_fallback': self.enable_web_fallback,
                'vector_service_status': self.vector_service.health_check(deep_check=False),
                'search_service_status': self.search_service.health_check(deep_check=False),
                'llm_service_status': self.llm_service.health_check(deep_check=False)
            }
            
        except Exception as e:
            logger.error(f"获取RAG统计信息失败: {str(e)}")
            return {'error': str(e)}
    
    def health_check(self, deep_check: bool = False) -> Dict[str, Any]:
        """
        健康检查
        
        Args:
            deep_check: 是否执行深度检查（包括实际的服务调用测试），默认False
        """
        try:
            # ✅ 执行各服务的健康检查，支持动态重连
            vector_status = self.vector_service.health_check(deep_check=deep_check)
            search_status = self.search_service.health_check(deep_check=deep_check)
            llm_status = self.llm_service.health_check(deep_check=deep_check)
            
            status = {
                'vector_service': vector_status,
                'search_service': search_status,
                'llm_service': llm_status,
                'config': {
                    'default_top_k': self.default_top_k,
                    'rerank_top_k': self.rerank_top_k,
                    'max_context_length': self.max_context_length,
                    'enable_rerank': self.enable_rerank,
                    'enable_web_fallback': self.enable_web_fallback
                }
            }
            
            # ✅ 智能健康状态判断
            vector_healthy = vector_status.get('embedding_model_loaded', False)
            search_healthy = search_status.get('search_test', False)
            llm_healthy = llm_status.get('model_test', False)
            
            # 如果LLM服务不可用，尝试重连
            if not llm_healthy and hasattr(self.llm_service, 'ensure_connection'):
                logger.info("LLM服务不可用，尝试重连...")
                if self.llm_service.ensure_connection():
                    # 重新检查LLM服务状态
                    llm_status = self.llm_service.health_check(deep_check=deep_check)
                    status['llm_service'] = llm_status
                    llm_healthy = llm_status.get('model_test', False)
                    logger.info(f"LLM服务重连结果: {'成功' if llm_healthy else '失败'}")
            
            # 整体健康状态
            all_healthy = vector_healthy and search_healthy and llm_healthy
            status['overall_health'] = all_healthy
            
            # ✅ 添加服务状态摘要
            status['service_summary'] = {
                'vector_service': 'healthy' if vector_healthy else 'unhealthy',
                'search_service': 'healthy' if search_healthy else 'unhealthy',
                'llm_service': 'healthy' if llm_healthy else 'unhealthy',
                'overall': 'healthy' if all_healthy else 'unhealthy'
            }
            
            return status
            
        except Exception as e:
            logger.error(f"RAG服务健康检查失败: {str(e)}")
            return {'error': str(e)}


# 全局RAG服务实例
rag_service = None


def get_rag_service() -> RAGService:
    """获取RAG服务实例"""
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service
