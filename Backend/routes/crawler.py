"""
爬虫相关API路由
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from Backend.models import db, RSSSource, CrawlTask
from Backend.services.crawler_service import CrawlerService
from Backend.services.data_service import DataService
from Backend.utils.decorators import jwt_required, admin_required
from Backend.utils.response import success_response, error_response

logger = logging.getLogger(__name__)

# 创建蓝图
crawler_bp = Blueprint('crawler', __name__, url_prefix='/api/crawler')

# 初始化服务
crawler_service = CrawlerService()
data_service = DataService()


@crawler_bp.route('/start', methods=['POST'])
@jwt_required()
def start_crawler_task():
    """启动爬虫任务"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('source_url'):
            return error_response('source_url 不能为空', 400)
        
        source_type = data.get('source_type', 'rss')
        source_url = data['source_url']
        category = data.get('category', '未分类')
        
        # 创建或获取 RSS 源
        rss_source = RSSSource.query.filter_by(url=source_url).first()
        
        if not rss_source:
            # 创建新的 RSS 源
            rss_source = RSSSource(
                name=data.get('name', f'RSS源-{source_url}'),
                url=source_url,
                category=category,
                is_active=True
            )
            db.session.add(rss_source)
            db.session.commit()
        
        # 创建爬虫任务
        task = CrawlTask(
            source_id=rss_source.id,
            task_type='manual',
            status='pending'
        )
        db.session.add(task)
        db.session.commit()
        
        return success_response({
            'task_id': task.id,
            'source_id': rss_source.id,
            'status': task.status
        }, message='爬虫任务创建成功', code=201)
        
    except Exception as e:
        logger.error(f"启动爬虫任务失败: {str(e)}")
        return error_response(f'启动爬虫任务失败: {str(e)}', 500)


@crawler_bp.route('/rss/sources', methods=['GET'])
@jwt_required()
def get_rss_sources():
    """获取RSS源列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        category = request.args.get('category')
        is_active = request.args.get('is_active')
        
        query = RSSSource.query
        
        if category:
            query = query.filter(RSSSource.category == category)
        
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true'
            query = query.filter(RSSSource.is_active == is_active_bool)
        
        # 分页查询
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        sources = [source.to_dict() for source in pagination.items]
        
        return success_response({
            'sources': sources,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"获取RSS源列表失败: {str(e)}")
        return error_response('获取RSS源列表失败', 500)


@crawler_bp.route('/rss/sources', methods=['POST'])
@jwt_required()
def create_rss_source():
    """创建RSS源"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['name', 'url']
        for field in required_fields:
            if field not in data or not data[field]:
                return error_response(f'缺少必需字段: {field}', 400)
        
        # 检查URL是否已存在
        existing_source = RSSSource.query.filter_by(url=data['url']).first()
        if existing_source:
            return error_response('该RSS源URL已存在', 400)
        
        # 创建RSS源
        rss_source = RSSSource(
            name=data['name'],
            url=data['url'],
            category=data.get('category'),
            is_active=data.get('is_active', True),
            crawl_frequency=data.get('crawl_frequency', 3600)
        )
        
        db.session.add(rss_source)
        db.session.commit()
        
        return success_response({
            'message': 'RSS源创建成功',
            'source': rss_source.to_dict()
        }, 201)
        
    except Exception as e:
        logger.error(f"创建RSS源失败: {str(e)}")
        db.session.rollback()
        return error_response('创建RSS源失败', 500)


@crawler_bp.route('/rss/sources/<int:source_id>', methods=['PUT'])
@jwt_required()
def update_rss_source(source_id):
    """更新RSS源"""
    try:
        rss_source = RSSSource.query.get_or_404(source_id)
        data = request.get_json()
        
        # 更新字段
        if 'name' in data:
            rss_source.name = data['name']
        if 'url' in data:
            # 检查URL是否与其他源冲突
            existing_source = RSSSource.query.filter(
                RSSSource.url == data['url'],
                RSSSource.id != source_id
            ).first()
            if existing_source:
                return error_response('该RSS源URL已被其他源使用', 400)
            rss_source.url = data['url']
        if 'category' in data:
            rss_source.category = data['category']
        if 'is_active' in data:
            rss_source.is_active = data['is_active']
        if 'crawl_frequency' in data:
            rss_source.crawl_frequency = data['crawl_frequency']
        
        db.session.commit()
        
        return success_response({
            'message': 'RSS源更新成功',
            'source': rss_source.to_dict()
        })
        
    except Exception as e:
        logger.error(f"更新RSS源失败: {str(e)}")
        db.session.rollback()
        return error_response('更新RSS源失败', 500)


@crawler_bp.route('/rss/sources/<int:source_id>', methods=['DELETE'])
@jwt_required()
def delete_rss_source(source_id):
    """删除RSS源"""
    try:
        rss_source = RSSSource.query.get_or_404(source_id)
        
        # 删除相关的爬取任务
        CrawlTask.query.filter_by(source_id=source_id).delete()
        
        db.session.delete(rss_source)
        db.session.commit()
        
        return success_response({'message': 'RSS源删除成功'})
        
    except Exception as e:
        logger.error(f"删除RSS源失败: {str(e)}")
        db.session.rollback()
        return error_response('删除RSS源失败', 500)


@crawler_bp.route('/rss/crawl', methods=['POST'])
@jwt_required()
def crawl_rss_feeds():
    """手动触发RSS抓取"""
    try:
        data = request.get_json() or {}
        source_ids = data.get('source_ids')
        
        # 获取要抓取的RSS源
        if source_ids:
            rss_sources = RSSSource.query.filter(
                RSSSource.id.in_(source_ids),
                RSSSource.is_active == True
            ).all()
        else:
            # 抓取所有活跃的RSS源
            rss_sources = RSSSource.query.filter_by(is_active=True).all()
        
        if not rss_sources:
            return error_response('没有找到可抓取的RSS源', 400)
        
        # 执行抓取
        result = crawler_service.fetch_rss_feeds(rss_sources)
        
        return success_response({
            'message': 'RSS抓取任务已启动',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"RSS抓取失败: {str(e)}")
        return error_response('RSS抓取失败', 500)


@crawler_bp.route('/rss/sources/<int:source_id>/crawl', methods=['POST'])
@jwt_required()
def crawl_single_rss_source(source_id):
    """抓取单个RSS源"""
    try:
        rss_source = RSSSource.query.get_or_404(source_id)
        
        if not rss_source.is_active:
            return error_response('RSS源未激活', 400)
        
        # 执行抓取
        result = crawler_service.fetch_rss_feeds([rss_source])
        
        return success_response({
            'message': f'RSS源 "{rss_source.name}" 抓取任务已启动',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"单个RSS源抓取失败: {str(e)}")
        return error_response('RSS源抓取失败', 500)


@crawler_bp.route('/web/crawl', methods=['POST'])
@jwt_required()
def crawl_webpage():
    """抓取单个网页"""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return error_response('缺少URL参数', 400)
        
        url = data['url']
        category = data.get('category')
        
        # 验证URL格式
        if not url.startswith(('http://', 'https://')):
            return error_response('无效的URL格式', 400)
        
        # 执行网页抓取
        result = crawler_service.crawl_webpage(url, category)
        
        # 添加详细日志
        logger.info(f"网页抓取结果: {result}")
        
        if result['success']:
            return success_response({
                'message': '网页抓取成功',
                'result': result
            })
        else:
            # 记录失败详情
            logger.error(f"网页抓取失败: URL={url}, 错误={result.get('message')}")
            return error_response(result['message'], 400)
        
    except Exception as e:
        logger.error(f"网页抓取失败: {str(e)}")
        return error_response('网页抓取失败', 500)


@crawler_bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_crawl_tasks():
    """获取爬取任务列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        task_type = request.args.get('task_type')
        
        query = CrawlTask.query
        
        if status:
            query = query.filter(CrawlTask.status == status)
        
        if task_type:
            query = query.filter(CrawlTask.task_type == task_type)
        
        # 分页查询
        pagination = query.order_by(CrawlTask.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        tasks = []
        for task in pagination.items:
            task_data = task.to_dict()
            if task.rss_source:
                task_data['source_name'] = task.rss_source.name
                task_data['source_url'] = task.rss_source.url
            tasks.append(task_data)
        
        return success_response({
            'tasks': tasks,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"获取爬取任务列表失败: {str(e)}")
        return error_response('获取爬取任务列表失败', 500)


@crawler_bp.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_crawl_task(task_id):
    """获取单个爬取任务详情"""
    try:
        task = db.session.get(CrawlTask, task_id)
        if not task:
            return error_response('爬取任务不存在', 404)
        
        task_data = task.to_dict()
        if task.rss_source:
            task_data['source_name'] = task.rss_source.name
            task_data['source_url'] = task.rss_source.url
            task_data['source_category'] = task.rss_source.category
        
        return success_response({'task': task_data})
        
    except Exception as e:
        logger.error(f"获取爬取任务详情失败: {str(e)}")
        return error_response('获取爬取任务详情失败', 500)


@crawler_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_crawl_statistics():
    """获取爬取统计信息"""
    try:
        stats = crawler_service.get_crawl_statistics()
        
        if 'error' in stats:
            return error_response(stats['error'], 500)
        
        return success_response({'statistics': stats})
        
    except Exception as e:
        logger.error(f"获取爬取统计信息失败: {str(e)}")
        return error_response('获取爬取统计信息失败', 500)


@crawler_bp.route('/monitor', methods=['GET'])
@jwt_required()
def monitor_crawl_tasks():
    """监控爬取任务"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        result = data_service.monitor_crawl_tasks(limit)
        
        if not result['success']:
            return error_response(result['error'], 500)
        
        return success_response(result)
        
    except Exception as e:
        logger.error(f"监控爬取任务失败: {str(e)}")
        return error_response('监控爬取任务失败', 500)


@crawler_bp.route('/schedule', methods=['POST'])
@jwt_required()
@admin_required()
def schedule_crawling():
    """调度定时爬取任务"""
    try:
        result = crawler_service.schedule_crawling_tasks()
        
        if result['success']:
            return success_response({
                'message': '定时爬取任务执行完成',
                'result': result
            })
        else:
            return error_response(result['message'], 500)
        
    except Exception as e:
        logger.error(f"调度定时爬取任务失败: {str(e)}")
        return error_response('调度定时爬取任务失败', 500)


@crawler_bp.route('/data-sources', methods=['GET'])
@jwt_required()
def get_data_sources():
    """获取数据源管理信息"""
    try:
        result = data_service.manage_data_sources()
        
        if not result['success']:
            return error_response(result['error'], 500)
        
        return success_response(result)
        
    except Exception as e:
        logger.error(f"获取数据源管理信息失败: {str(e)}")
        return error_response('获取数据源管理信息失败', 500)


@crawler_bp.route('/data-quality', methods=['GET'])
@jwt_required()
def check_data_quality():
    """检查数据质量"""
    try:
        data_type = request.args.get('data_type', 'all')
        
        result = data_service.check_data_quality(data_type)
        
        if not result['success']:
            return error_response(result['error'], 500)
        
        return success_response(result)
        
    except Exception as e:
        logger.error(f"检查数据质量失败: {str(e)}")
        return error_response('检查数据质量失败', 500)


@crawler_bp.route('/tasks/clear', methods=['DELETE'])
@jwt_required()
def clear_all_tasks():
    """清空所有任务记录"""
    try:
        # 删除所有任务记录
        deleted_count = CrawlTask.query.delete()
        db.session.commit()
        
        logger.info(f"已清空 {deleted_count} 条任务记录")
        
        return success_response({
            'message': f'已清空 {deleted_count} 条任务记录',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        logger.error(f"清空任务记录失败: {str(e)}")
        db.session.rollback()
        return error_response('清空任务记录失败', 500)
