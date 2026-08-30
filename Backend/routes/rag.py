"""
RAG问答API路由
提供检索增强生成问答功能
"""

from flask import Blueprint, request, jsonify, Response, stream_template
from marshmallow import Schema, fields, validate
import json
import logging

from Backend.services.rag_service import get_rag_service
from Backend.utils.response import success_response, error_response
from Backend.utils.decorators import jwt_required, validate_json

logger = logging.getLogger(__name__)

# 创建RAG蓝图
rag_bp = Blueprint('rag', __name__, url_prefix='/api/rag')


def _rag_result_response(result):
    """Return a structured failure when the RAG service reports an error."""
    error = result.get('error') if isinstance(result, dict) else None
    if not error:
        return success_response(result)

    error_code = result.get('error_code', 'RAG_REQUEST_FAILED')
    status_code = 503 if error_code == 'AI_DEPENDENCY_UNAVAILABLE' else 500
    message = (
        'AI服务暂时不可用，请稍后重试。'
        if status_code == 503
        else 'RAG问答失败，请稍后重试。'
    )
    return error_response(message, status_code, data={'error_code': error_code})


class RAGQuerySchema(Schema):
    """RAG查询验证模式"""
    query = fields.Str(required=True, validate=validate.Length(min=1, max=1000))
    top_k = fields.Int(validate=validate.Range(min=1, max=50), load_default=20)
    enable_rerank = fields.Bool(load_default=True)
    enable_web_fallback = fields.Bool(load_default=False)
    stream = fields.Bool(load_default=False)
    options = fields.Dict(load_default={})


@rag_bp.route('/ask', methods=['POST'])
@jwt_required()
@validate_json(RAGQuerySchema)
def ask_question():
    """RAG问答接口"""
    try:
        import time
        request_start_time = time.time()
        
        data = request.get_json()
        logger.info(f"收到RAG问答请求: query={data.get('query', '')[:50]}...")
        logger.info(f"完整请求数据: {data}")
        query = data['query']
        top_k = data.get('top_k', 20)
        enable_rerank = data.get('enable_rerank', True)
        enable_web_fallback = data.get('enable_web_fallback', False)
        stream = data.get('stream', False)
        options = data.get('options', {})
        
        logger.info(f"RAG请求参数: top_k={top_k}, enable_rerank={enable_rerank}, enable_web_fallback={enable_web_fallback}, stream={stream}")
        
        # 获取用户ID
        user_id = getattr(request, 'current_user_id', None)
        
        # 构建选项
        rag_options = {
            'top_k': top_k,
            'enable_rerank': enable_rerank,
            'enable_web_fallback': enable_web_fallback,
            **options
        }
        
        # 获取RAG服务
        rag_service = get_rag_service()
        
        if stream:
            # 流式响应
            from flask import current_app, copy_current_request_context
            
            # 保存当前应用的引用
            app = current_app._get_current_object()
            
            def generate():
                try:
                    # 在生成器中确保有应用上下文
                    with app.app_context():
                        for chunk in rag_service.stream_answer(query, user_id, rag_options):
                            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.error(f"流式响应生成错误: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    error_chunk = {'type': 'error', 'message': f'应用错误: {str(e)}'}
                    yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
            
            return Response(
                generate(),
                mimetype='text/plain',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*'
                }
            )
        else:
            # 普通响应
            logger.info("开始执行RAG问答流程")
            result = rag_service.answer_question(query, user_id, rag_options)
            
            request_time = time.time() - request_start_time
            logger.info(f"RAG请求完成，总耗时: {request_time:.2f}秒")
            
            return _rag_result_response(result)
        
    except Exception as e:
        logger.error(f"RAG问答失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(f"RAG问答失败: {str(e)}", 500)


@rag_bp.route('/context', methods=['POST'])
@jwt_required()
def build_context():
    """构建上下文接口"""
    try:
        data = request.get_json()
        documents = data.get('documents', [])
        max_length = data.get('max_length', 4000)
        
        if not documents:
            return error_response('缺少文档数据', 400)
        
        # 获取RAG服务
        rag_service = get_rag_service()
        
        # 构建上下文
        context = rag_service.build_context(documents)
        
        return success_response({
            'context': context,
            'context_length': sum(len(str(doc)) for doc in context),
            'max_length': max_length
        })
        
    except Exception as e:
        logger.error(f"构建上下文失败: {str(e)}")
        return error_response(f"构建上下文失败: {str(e)}", 500)


@rag_bp.route('/vector-search', methods=['POST'])
@jwt_required()
def vector_search():
    """向量检索接口"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        top_k = data.get('top_k', 20)
        
        if not query:
            return error_response('缺少查询参数', 400)
        
        # 获取RAG服务
        rag_service = get_rag_service()
        
        # 执行向量检索
        results = rag_service.integrate_vector_search(query, top_k)
        
        return success_response(results)
        
    except Exception as e:
        logger.error(f"向量检索失败: {str(e)}")
        return error_response(f"向量检索失败: {str(e)}", 500)


@rag_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_answer():
    """LLM生成接口"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        context = data.get('context', [])
        options = data.get('options', {})
        
        if not query:
            return error_response('缺少查询参数', 400)
        
        # 获取RAG服务
        rag_service = get_rag_service()
        
        # 执行LLM生成
        result = rag_service.integrate_llm_generation(query, context, options)
        
        return _rag_result_response(result)
        
    except Exception as e:
        logger.error(f"LLM生成失败: {str(e)}")
        return error_response(f"LLM生成失败: {str(e)}", 500)


@rag_bp.route('/validate', methods=['POST'])
@jwt_required()
def validate_response():
    """响应验证接口"""
    try:
        data = request.get_json()
        response = data.get('response', {})
        query = data.get('query', '')
        context = data.get('context', [])
        
        if not response:
            return error_response('缺少响应数据', 400)
        
        # 获取RAG服务
        rag_service = get_rag_service()
        
        # 执行响应验证
        validated_response = rag_service.validate_response(response, query, context)
        
        return success_response(validated_response)
        
    except Exception as e:
        logger.error(f"响应验证失败: {str(e)}")
        return error_response(f"响应验证失败: {str(e)}", 500)


@rag_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_rag_stats():
    """获取RAG统计信息"""
    try:
        # 获取RAG服务
        rag_service = get_rag_service()
        
        # 获取统计信息
        stats = rag_service.get_rag_stats()
        
        return success_response(stats)
        
    except Exception as e:
        logger.error(f"获取RAG统计失败: {str(e)}")
        return error_response(f"获取RAG统计失败: {str(e)}", 500)


@rag_bp.route('/health', methods=['GET'])
def rag_health_check():
    """
    RAG服务健康检查
    
    查询参数：
    - deep_check: 是否执行深度检查（默认false，快速模式）
    - retry: 是否在服务不可用时尝试重连（默认true）
    """
    try:
        # 获取参数
        deep_check = request.args.get('deep_check', 'false').lower() == 'true'
        retry_enabled = request.args.get('retry', 'true').lower() == 'true'
        
        # 获取RAG服务
        rag_service = get_rag_service()
        
        # 执行健康检查（传递deep_check参数）
        health_status = rag_service.health_check(deep_check=deep_check)
        
        # ✅ 如果启用重试且整体健康状态为false，尝试重连
        if retry_enabled and not health_status.get('overall_health', False):
            logger.info("检测到服务不健康，尝试重连...")
            
            # 重新执行健康检查，这次会触发重连逻辑
            retry_status = rag_service.health_check(deep_check=deep_check)
            
            # 如果重连成功，更新状态
            if retry_status.get('overall_health', False):
                logger.info("服务重连成功，状态已更新")
                health_status = retry_status
        
        return success_response(health_status)
        
    except Exception as e:
        logger.error(f"RAG服务健康检查失败: {str(e)}")
        return error_response(f"RAG服务健康检查失败: {str(e)}", 500)


@rag_bp.route('/test', methods=['POST'])
@jwt_required()
def test_rag_pipeline():
    """测试RAG流程"""
    try:
        data = request.get_json()
        query = data.get('query', '测试查询')
        
        # 获取RAG服务
        rag_service = get_rag_service()
        
        # 执行测试
        test_result = rag_service.answer_question(query, options={'top_k': 5})
        
        return success_response({
            'test_query': query,
            'result': test_result,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"RAG流程测试失败: {str(e)}")
        return error_response(f"RAG流程测试失败: {str(e)}", 500)
