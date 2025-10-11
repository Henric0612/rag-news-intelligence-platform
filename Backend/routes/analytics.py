"""
数据分析路由
提供知识库数据分析和可视化API
"""
from flask import Blueprint, request, jsonify
from Backend.utils.decorators import jwt_required
from Backend.utils.response import success_response, error_response
from Backend.services.analytics_service import get_analytics_service
import logging

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


@analytics_bp.route('/clustering', methods=['GET'])
@jwt_required()
def get_clustering_analysis():
    """
    获取聚类分析报告
    包含Top10关键词、聚类分布等信息
    
    Query Parameters:
        limit (int, optional): 限制分析的文档数量
    """
    try:
        # 获取查询参数
        limit = request.args.get('limit', type=int)
        
        # 获取分析服务
        analytics_service = get_analytics_service()
        
        # 生成聚类分析报告
        report = analytics_service.get_clustering_report(limit=limit)
        
        if report.get('success'):
            return success_response(
                data=report,
                message='聚类分析报告生成成功'
            )
        else:
            return error_response(
                message=report.get('message', '生成聚类分析报告失败'),
                code=500
            )
        
    except Exception as e:
        logger.error(f"获取聚类分析报告失败: {str(e)}")
        return error_response(
            message=f'获取聚类分析报告失败: {str(e)}',
            code=500
        )


@analytics_bp.route('/keywords', methods=['GET'])
@jwt_required()
def get_top_keywords():
    """
    获取Top关键词（快速接口）
    
    Query Parameters:
        limit (int, optional): 限制分析的文档数量
    """
    try:
        limit = request.args.get('limit', type=int)
        
        analytics_service = get_analytics_service()
        report = analytics_service.get_clustering_report(limit=limit)
        
        if report.get('success'):
            return success_response(
                data={
                    'top_10_keywords': report.get('top_10_keywords', []),
                    'total_items': report.get('total_items', 0)
                },
                message='Top关键词获取成功'
            )
        else:
            return error_response(
                message=report.get('message', '获取关键词失败'),
                code=500
            )
        
    except Exception as e:
        logger.error(f"获取Top关键词失败: {str(e)}")
        return error_response(
            message=f'获取Top关键词失败: {str(e)}',
            code=500
        )


@analytics_bp.route('/trends', methods=['GET'])
@jwt_required()
def get_trend_analysis():
    """
    获取趋势分析数据
    
    Query Parameters:
        days (int, optional): 分析的天数，默认30天
    """
    try:
        days = request.args.get('days', default=30, type=int)
        
        # 验证参数
        if days < 1 or days > 365:
            return error_response(
                message='天数参数必须在1-365之间',
                code=400
            )
        
        analytics_service = get_analytics_service()
        result = analytics_service.get_trend_analysis(days=days)
        
        if result.get('success'):
            return success_response(
                data=result,
                message='趋势分析数据获取成功'
            )
        else:
            return error_response(
                message='获取趋势分析数据失败',
                code=500
            )
        
    except Exception as e:
        logger.error(f"获取趋势分析失败: {str(e)}")
        return error_response(
            message=f'获取趋势分析失败: {str(e)}',
            code=500
        )


@analytics_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_statistics():
    """
    获取知识库统计信息
    包含总量、分类分布、来源类型分布等
    """
    try:
        analytics_service = get_analytics_service()
        report = analytics_service.get_clustering_report(limit=None)
        
        if report.get('success'):
            statistics = {
                'total_items': report.get('total_items', 0),
                'category_distribution': report.get('category_distribution', []),
                'source_type_distribution': report.get('source_type_distribution', []),
                'unique_keywords': report.get('unique_keywords', 0)
            }
            
            return success_response(
                data=statistics,
                message='统计信息获取成功'
            )
        else:
            return error_response(
                message='获取统计信息失败',
                code=500
            )
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        return error_response(
            message=f'获取统计信息失败: {str(e)}',
            code=500
        )


@analytics_bp.route('/health', methods=['GET'])
def health_check():
    """数据分析服务健康检查"""
    try:
        analytics_service = get_analytics_service()
        health_status = analytics_service.health_check()
        
        return success_response(
            data=health_status,
            message='数据分析服务正常'
        )
        
    except Exception as e:
        logger.error(f"数据分析服务健康检查失败: {str(e)}")
        return error_response(
            message=f'数据分析服务健康检查失败: {str(e)}',
            code=500
        )

