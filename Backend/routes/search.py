"""
搜索API路由
提供智能搜索、语义检索等功能
"""

from flask import Blueprint, request, jsonify, current_app
from marshmallow import Schema, fields, validate
import logging

from Backend.services.search_service import get_search_service
from Backend.utils.response import success_response, error_response
from Backend.utils.decorators import jwt_required, validate_json

logger = logging.getLogger(__name__)

# 创建搜索蓝图
search_bp = Blueprint('search', __name__, url_prefix='/api/search')


class SearchQuerySchema(Schema):
    """搜索查询验证模式"""
    query = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    top_k = fields.Int(validate=validate.Range(min=1, max=50), load_default=20)
    filters = fields.Dict(load_default={})
    search_type = fields.Str(validate=validate.OneOf(['semantic', 'keyword', 'hybrid']), load_default='semantic')


class SearchSuggestionsSchema(Schema):
    """搜索建议验证模式"""
    query = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    limit = fields.Int(validate=validate.Range(min=1, max=20), load_default=10)


@search_bp.route('/query', methods=['POST'])
@jwt_required()
@validate_json(SearchQuerySchema)
def search_query():
    """智能搜索接口"""
    try:
        data = request.get_json()
        query = data['query']
        top_k = data.get('top_k', 20)
        filters = data.get('filters', {})
        search_type = data.get('search_type', 'semantic')
        
        # 获取用户ID
        user_id = getattr(request, 'current_user_id', None)
        
        # 获取搜索服务
        search_service = get_search_service()
        
        # 根据搜索类型执行搜索
        if search_type == 'semantic':
            results = search_service.semantic_search(query, top_k, filters, user_id)
        elif search_type == 'keyword':
            results = search_service._keyword_search(query, filters, top_k)
            results = {
                'query': query,
                'results': results,
                'total': len(results),
                'response_time': 0,
                'search_type': 'keyword'
            }
        elif search_type == 'hybrid':
            results = search_service.hybrid_search(query, filters, top_k)
        else:
            return error_response('不支持的搜索类型', 400)
        
        # 记录搜索历史
        if 'results' in results:
            search_service._record_search_history(
                query, 
                len(results['results']), 
                results.get('response_time', 0), 
                user_id
            )
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        return error_response(f"搜索失败: {str(e)}", 500)


@search_bp.route('/suggestions', methods=['GET'])
@jwt_required()
def get_search_suggestions():
    """获取搜索建议"""
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if not query or len(query) < 2:
            return success_response([])
        
        # 获取搜索服务
        search_service = get_search_service()
        
        # 获取搜索建议
        suggestions = search_service.get_search_suggestions(query, limit)
        
        return success_response(suggestions)
        
    except Exception as e:
        logger.error(f"获取搜索建议失败: {str(e)}")
        return error_response(f"获取搜索建议失败: {str(e)}", 500)


@search_bp.route('/history', methods=['GET'])
@jwt_required()
def get_search_history():
    """获取搜索历史"""
    try:
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 20))
        
        # 获取用户ID
        user_id = getattr(request, 'current_user_id', None)
        
        # 查询搜索历史
        from Backend.models.search_history import SearchHistory
        from Backend.models import db
        
        query = db.session.query(SearchHistory).filter(
            SearchHistory.user_id == user_id
        ).order_by(SearchHistory.created_at.desc())
        
        # 分页
        total = query.count()
        history = query.offset((page - 1) * size).limit(size).all()
        
        # 格式化结果
        history_data = []
        for item in history:
            history_data.append({
                'id': item.id,
                'query': item.query,
                'results_count': item.results_count,
                'response_time': item.response_time,
                'created_at': item.created_at.isoformat()
            })
        
        return success_response({
            'history': history_data,
            'total': total,
            'page': page,
            'size': size,
            'pages': (total + size - 1) // size
        })
        
    except Exception as e:
        logger.error(f"获取搜索历史失败: {str(e)}")
        return error_response(f"获取搜索历史失败: {str(e)}", 500)


@search_bp.route('/rerank', methods=['POST'])
@jwt_required()
def rerank_results():
    """结果重排接口"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        results = data.get('results', [])
        top_k = data.get('top_k', 5)
        
        if not query or not results:
            return error_response('缺少必要参数', 400)
        
        # 获取搜索服务
        search_service = get_search_service()
        
        # 执行重排
        reranked_results = search_service.rerank_results(query, results, top_k)
        
        return success_response({
            'query': query,
            'results': reranked_results,
            'total': len(reranked_results)
        })
        
    except Exception as e:
        logger.error(f"结果重排失败: {str(e)}")
        return error_response(f"结果重排失败: {str(e)}", 500)


@search_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_search_stats():
    """获取搜索统计信息"""
    try:
        # 获取用户ID
        user_id = getattr(request, 'current_user_id', None)
        
        # 查询搜索统计
        from Backend.models.search_history import SearchHistory
        from Backend.models import db
        from sqlalchemy import func
        
        # 总搜索次数
        total_searches = db.session.query(func.count(SearchHistory.id)).filter(
            SearchHistory.user_id == user_id
        ).scalar()
        
        # 平均响应时间
        avg_response_time = db.session.query(func.avg(SearchHistory.response_time)).filter(
            SearchHistory.user_id == user_id
        ).scalar()
        
        # 最近搜索
        recent_searches = db.session.query(SearchHistory).filter(
            SearchHistory.user_id == user_id
        ).order_by(SearchHistory.created_at.desc()).limit(5).all()
        
        recent_queries = [item.query for item in recent_searches]
        
        return success_response({
            'total_searches': total_searches or 0,
            'avg_response_time': round(avg_response_time or 0, 3),
            'recent_queries': recent_queries
        })
        
    except Exception as e:
        logger.error(f"获取搜索统计失败: {str(e)}")
        return error_response(f"获取搜索统计失败: {str(e)}", 500)


@search_bp.route('/health', methods=['GET'])
def search_health_check():
    """搜索服务健康检查"""
    try:
        search_service = get_search_service()
        health_status = search_service.health_check()
        
        return success_response(health_status)
        
    except Exception as e:
        logger.error(f"搜索服务健康检查失败: {str(e)}")
        return error_response(f"搜索服务健康检查失败: {str(e)}", 500)
