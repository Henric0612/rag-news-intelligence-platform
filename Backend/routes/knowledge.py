"""
知识库路由
"""
from flask import Blueprint, request
from Backend.services.knowledge_service import KnowledgeService
from Backend.utils.response import success_response, error_response
from Backend.utils.decorators import jwt_required

knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/api/knowledge')


@knowledge_bp.route('', methods=['GET'])
@jwt_required()
def get_knowledge_items():
    """获取知识库列表"""
    try:
        # 获取分页参数（支持 per_page 和 size 两种参数名，per_page 优先）
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', request.args.get('size', 20, type=int), type=int)
        
        # 获取筛选参数
        filters = {}
        if request.args.get('category'):
            filters['category'] = request.args.get('category')
        if request.args.get('source_type'):
            filters['source_type'] = request.args.get('source_type')
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        
        # 获取搜索关键词
        keyword = request.args.get('keyword', '').strip()
        if keyword:
            filters['keyword'] = keyword
        
        # 获取知识库列表
        result = KnowledgeService.get_knowledge_items(
            page=page,
            per_page=per_page,
            **filters
        )
        
        return success_response(result)
        
    except Exception as e:
        return error_response(f'获取知识库列表失败: {str(e)}', 500)


@knowledge_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_knowledge_item(item_id):
    """获取单个知识库条目"""
    try:
        item = KnowledgeService.get_knowledge_item_by_id(item_id)
        
        if not item:
            return error_response('知识库条目不存在', 404)
        
        return success_response(item.to_dict())
        
    except Exception as e:
        return error_response(f'获取知识库条目失败: {str(e)}', 500)


@knowledge_bp.route('', methods=['POST'])
@jwt_required()
def create_knowledge_item():
    """创建知识库条目"""
    from Backend.models import User
    
    data = request.get_json()
    
    # 验证必填字段
    if not data.get('title') or not data.get('content'):
        return error_response('标题和内容不能为空', 400)
    
    try:
        # 获取当前用户邮箱（用于发送入库通知）
        user_id = getattr(request, 'current_user_id', None)
        user_email = None
        if user_id:
            from Backend.models import db
            user = db.session.get(User, user_id)
            if user:
                user_email = user.email
        
        # 创建知识库条目
        item = KnowledgeService.create_knowledge_item(
            title=data['title'],
            content=data['content'],
            user_email=user_email,  # 传递用户邮箱
            summary=data.get('summary'),
            source_url=data.get('source_url'),
            source_name=data.get('source_name'),
            source_type=data.get('source_type', 'manual'),
            category=data.get('category'),
            tags=data.get('tags')
        )
        
        return success_response(item.to_dict(), message='创建成功', code=201)
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f'创建失败: {str(e)}', 500)


@knowledge_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_knowledge_item(item_id):
    """更新知识库条目"""
    data = request.get_json()
    
    try:
        # 更新知识库条目
        item = KnowledgeService.update_knowledge_item(item_id, **data)
        
        return success_response(item.to_dict(), message='更新成功')
        
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(f'更新失败: {str(e)}', 500)


@knowledge_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_knowledge_item(item_id):
    """删除知识库条目"""
    try:
        KnowledgeService.delete_knowledge_item(item_id)
        
        return success_response(message='删除成功')
        
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(f'删除失败: {str(e)}', 500)


@knowledge_bp.route('/batch', methods=['DELETE'])
@jwt_required()
def batch_delete_knowledge_items():
    """批量删除知识库条目"""
    try:
        data = request.get_json()
        
        if not data or 'ids' not in data:
            return error_response('缺少ids参数', 400)
        
        ids = data['ids']
        
        if not isinstance(ids, list) or len(ids) == 0:
            return error_response('ids必须是非空数组', 400)
        
        # 批量删除
        deleted_count = 0
        failed_count = 0
        errors = []
        
        for item_id in ids:
            try:
                KnowledgeService.delete_knowledge_item(item_id)
                deleted_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f'ID {item_id}: {str(e)}')
        
        if failed_count == 0:
            return success_response({
                'message': f'成功删除 {deleted_count} 条记录',
                'deleted_count': deleted_count
            })
        else:
            return success_response({
                'message': f'删除完成：成功 {deleted_count} 条，失败 {failed_count} 条',
                'deleted_count': deleted_count,
                'failed_count': failed_count,
                'errors': errors
            })
        
    except Exception as e:
        return error_response(f'批量删除失败: {str(e)}', 500)


@knowledge_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_statistics():
    """获取知识库统计信息"""
    try:
        stats = KnowledgeService.get_statistics()
        
        return success_response(stats)
        
    except Exception as e:
        return error_response(f'获取统计信息失败: {str(e)}', 500)


@knowledge_bp.route('/<int:item_id>/sync-vector', methods=['POST'])
@jwt_required()
def sync_vector_for_item(item_id):
    """为单个条目同步向量"""
    try:
        data = request.get_json() or {}
        force_resync = data.get('force_resync', False)
        
        result = KnowledgeService.sync_vector_for_item(item_id, force_resync=force_resync)
        
        return success_response(result, message=result['message'])
        
    except ValueError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(f'向量同步失败: {str(e)}', 500)


@knowledge_bp.route('/batch-sync', methods=['POST'])
@jwt_required()
def batch_sync_vectors():
    """批量同步向量索引"""
    try:
        data = request.get_json() or {}
        
        item_ids = data.get('ids')  # 可选，指定要同步的条目ID列表
        only_unprocessed = data.get('only_unprocessed', True)  # 默认仅处理未向量化的
        force_resync = data.get('force_resync', False)  # 是否强制重新同步
        rebuild_index = data.get('rebuild_index', False)  # 是否完全重建向量索引
        
        result = KnowledgeService.batch_sync_vectors(
            item_ids=item_ids,
            only_unprocessed=only_unprocessed,
            force_resync=force_resync,
            rebuild_index=rebuild_index
        )
        
        return success_response(result, message=result['message'])
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f'批量同步失败: {str(e)}', 500)