"""
知识库服务
"""
from Backend.models import KnowledgeItem, db
from Backend.utils.text_utils import generate_content_hash
from Backend.utils.content_quality import assess_content_quality
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class KnowledgeService:
    """知识库管理服务"""
    
    @staticmethod
    def create_knowledge_item(title, content, user_email=None, **kwargs):
        """创建知识库条目并发送邮件通知"""
        # 生成内容哈希
        content_hash = generate_content_hash(content)
        
        # 检查是否已存在
        existing = KnowledgeItem.query.filter_by(content_hash=content_hash).first()
        if existing:
            raise ValueError('内容已存在')
        
        # 评估内容质量
        quality_result = assess_content_quality(content, title)
        quality_score = quality_result['quality_score']
        
        # 创建知识库条目
        item = KnowledgeItem(
            title=title,
            content=content,
            content_hash=content_hash,
            quality_score=quality_score,
            markdown_content=kwargs.pop('markdown_content', None),
            **kwargs
        )
        
        db.session.add(item)
        db.session.commit()
        
        # 自动向量化处理
        try:
            from Backend.services.vector_service import get_vector_service
            vector_service = get_vector_service()
            vector_id = vector_service.add_document(item.id, content)
            
            # 更新向量ID和状态
            item.vector_id = vector_id
            item.status = 'processed'
            item.processed_at = datetime.now(timezone.utc)
            db.session.commit()
            
            logger.info(f"知识库条目 {item.id} 向量化成功，vector_id: {vector_id}")
        except Exception as e:
            logger.error(f"知识库条目 {item.id} 向量化失败: {str(e)}")
            # 向量化失败不影响创建流程
        
        # 异步发送邮件通知（不影响主流程）
        # 在测试环境中跳过邮件发送以提高测试速度
        from flask import current_app
        if user_email and not current_app.config.get('TESTING', False):
            try:
                KnowledgeService._send_knowledge_added_notification(item, user_email)
            except Exception as e:
                logger.warning(f"发送入库通知邮件失败: {str(e)}")
        
        return item
    
    @staticmethod
    def _send_knowledge_added_notification(item: KnowledgeItem, user_email: str):
        """发送知识库入库通知邮件"""
        try:
            from Backend.services.email_service import EmailService
            from flask import current_app
            
            email_service = EmailService()
            
            # 构建邮件内容
            content_preview = item.content[:200] + '...' if len(item.content) > 200 else item.content
            
            html_content = f"""
            <html>
            <body>
                <h2>知识库入库通知</h2>
                <p>您好！</p>
                <p>以下内容已成功添加到知识库：</p>
                <div style="border-left: 3px solid #4CAF50; padding-left: 15px; margin: 20px 0;">
                    <h3>{item.title}</h3>
                    <p><strong>来源类型：</strong>{item.source_type}</p>
                    <p><strong>分类：</strong>{item.category or '未分类'}</p>
                    <p><strong>入库时间：</strong>{item.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>内容预览：</strong></p>
                    <p style="color: #666;">{content_preview}</p>
                </div>
                <p>您可以登录系统查看完整内容。</p>
                <p>此邮件由系统自动发送，请勿回复。</p>
            </body>
            </html>
            """
            
            text_content = f"""
            知识库入库通知
            
            您好！
            
            以下内容已成功添加到知识库：
            
            标题：{item.title}
            来源类型：{item.source_type}
            分类：{item.category or '未分类'}
            入库时间：{item.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            
            内容预览：
            {content_preview}
            
            您可以登录系统查看完整内容。
            
            此邮件由系统自动发送，请勿回复。
            """
            
            success = email_service.send_email(
                to_email=user_email,
                subject=f'知识库入库通知 - {item.title}',
                html_content=html_content,
                text_content=text_content
            )
            
            if success:
                logger.info(f"成功发送入库通知邮件到 {user_email}")
            else:
                logger.warning(f"发送入库通知邮件到 {user_email} 失败")
                
        except Exception as e:
            logger.error(f"发送入库通知邮件异常: {str(e)}")
            raise
    
    @staticmethod
    def get_knowledge_items(page=1, per_page=20, **filters):
        """获取知识库列表（支持关键词搜索）"""
        query = KnowledgeItem.query
        
        # 应用筛选条件
        if filters.get('category'):
            query = query.filter_by(category=filters['category'])
        
        if filters.get('source_type'):
            query = query.filter_by(source_type=filters['source_type'])
        
        if filters.get('status'):
            query = query.filter_by(status=filters['status'])
        
        # 关键词搜索（支持标题、内容、摘要）
        keyword = filters.get('keyword', '').strip()
        if keyword:
            # 使用 ilike 进行大小写不敏感的模糊搜索
            search_pattern = f'%{keyword}%'
            query = query.filter(
                db.or_(
                    KnowledgeItem.title.ilike(search_pattern),
                    KnowledgeItem.content.ilike(search_pattern),
                    KnowledgeItem.summary.ilike(search_pattern)
                )
            )
            logger.info(f"应用关键词搜索: {keyword}")
        
        # 排序
        query = query.order_by(KnowledgeItem.created_at.desc())
        
        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'items': [item.to_dict(include_content=False) for item in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def get_knowledge_item_by_id(item_id):
        """获取单个知识库条目"""
        return db.session.get(KnowledgeItem, item_id)
    
    @staticmethod
    def update_knowledge_item(item_id, **updates):
        """更新知识库条目"""
        item = db.session.get(KnowledgeItem, item_id)
        if not item:
            raise ValueError('知识库条目不存在')
        
        # 检查content是否被修改
        content_changed = 'content' in updates and updates['content'] != item.content
        old_vector_id = item.vector_id
        new_content = updates.get('content', item.content)
        
        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)
        
        item.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # 如果内容被修改，重新向量化
        if content_changed:
            try:
                from Backend.services.vector_service import get_vector_service
                vector_service = get_vector_service()
                
                # 删除旧向量
                if old_vector_id is not None:
                    vector_service.delete_document(old_vector_id)
                    logger.info(f"删除旧向量 {old_vector_id}")
                
                # 创建新向量
                vector_id = vector_service.add_document(item.id, new_content)
                
                # 更新向量ID和状态
                item.vector_id = vector_id
                item.status = 'processed'
                item.processed_at = datetime.now(timezone.utc)
                db.session.commit()
                
                logger.info(f"知识库条目 {item.id} 重新向量化成功，新 vector_id: {vector_id}")
            except Exception as e:
                logger.error(f"知识库条目 {item.id} 重新向量化失败: {str(e)}")
                # 向量化失败不影响更新流程
        
        return item
    
    @staticmethod
    def delete_knowledge_item(item_id):
        """删除知识库条目"""
        item = db.session.get(KnowledgeItem, item_id)
        if not item:
            raise ValueError('知识库条目不存在')
        
        # 删除对应的向量
        if item.vector_id is not None:
            try:
                from Backend.services.vector_service import get_vector_service
                vector_service = get_vector_service()
                vector_service.delete_document(item.vector_id)
                logger.info(f"删除知识库条目 {item.id} 的向量 {item.vector_id}")
            except Exception as e:
                logger.error(f"删除向量失败: {str(e)}")
                # 向量删除失败不影响条目删除
        
        db.session.delete(item)
        db.session.commit()
        
        return True
    
    @staticmethod
    def get_statistics():
        """获取知识库统计信息"""
        from Backend.models import RSSSource
        
        total = KnowledgeItem.query.count()
        by_type = db.session.query(
            KnowledgeItem.source_type,
            db.func.count(KnowledgeItem.id)
        ).group_by(KnowledgeItem.source_type).all()
        
        by_category = db.session.query(
            KnowledgeItem.category,
            db.func.count(KnowledgeItem.id)
        ).group_by(KnowledgeItem.category).all()
        
        # 向量同步统计
        vectorized_count = KnowledgeItem.query.filter(
            KnowledgeItem.vector_id.isnot(None)
        ).count()
        not_vectorized_count = total - vectorized_count
        
        # 活跃RSS源统计（与数据采集页面保持一致）
        active_rss_sources = RSSSource.query.filter_by(is_active=True).count()
        
        return {
            'total': total,
            'by_source_type': {k: v for k, v in by_type},
            'by_category': {k: v for k, v in by_category if k},
            'vectorized': vectorized_count,
            'not_vectorized': not_vectorized_count,
            'active_sources': active_rss_sources  # 活跃的RSS源数量
        }
    
    @staticmethod
    def sync_vector_for_item(item_id, force_resync=False):
        """为单个知识库条目同步向量"""
        item = db.session.get(KnowledgeItem, item_id)
        if not item:
            raise ValueError('知识库条目不存在')
        
        # 检查是否需要同步
        if not force_resync and item.vector_id is not None:
            return {
                'success': True,
                'message': '条目已有向量，无需同步',
                'item_id': item_id,
                'vector_id': item.vector_id,
                'skipped': True
            }
        
        try:
            from Backend.services.vector_service import get_vector_service
            vector_service = get_vector_service()
            
            # 如果是强制重新同步，先删除旧向量并清空 vector_id
            if force_resync and item.vector_id is not None:
                old_vector_id = item.vector_id
                try:
                    # 先将数据库中的 vector_id 设为 None，避免唯一性约束冲突
                    item.vector_id = None
                    db.session.flush()
                    # 然后删除向量映射
                    vector_service.delete_document(old_vector_id)
                    logger.info(f"删除旧向量 {old_vector_id} (强制重新同步)")
                except Exception as e:
                    logger.warning(f"删除旧向量失败: {str(e)}")
            
            # 创建新向量
            vector_id = vector_service.add_document(item.id, item.content)
            
            # 更新数据库
            item.vector_id = vector_id
            item.status = 'processed'
            item.processed_at = datetime.now(timezone.utc)
            db.session.commit()
            
            logger.info(f"知识库条目 {item_id} 向量同步成功，vector_id: {vector_id}")
            
            return {
                'success': True,
                'message': '向量同步成功',
                'item_id': item_id,
                'vector_id': vector_id,
                'skipped': False
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"向量同步失败: {str(e)}")
            raise ValueError(f'向量同步失败: {str(e)}')
    
    @staticmethod
    def batch_sync_vectors(item_ids=None, only_unprocessed=True, force_resync=False, rebuild_index=False):
        """
        批量同步向量索引
        
        Args:
            item_ids: 要同步的条目ID列表（None表示全部）
            only_unprocessed: 仅处理未向量化的条目
            force_resync: 强制重新同步已有向量的条目
            rebuild_index: 完全重建向量索引（清空后重建）
        """
        try:
            # 如果是完全重建模式
            if rebuild_index:
                logger.info("🔄 开始完全重建向量索引...")
                
                from Backend.services.vector_service import get_vector_service
                vector_service = get_vector_service()
                
                # 1. 清空向量索引
                logger.info("📝 步骤 1/3: 清空向量索引...")
                vector_service.clear_index()
                
                # 2. 清空所有知识库条目的 vector_id 和 status
                logger.info("📝 步骤 2/3: 重置数据库向量状态...")
                items = KnowledgeItem.query.all()
                for item in items:
                    item.vector_id = None
                    item.status = 'pending'
                db.session.commit()
                logger.info(f"✅ 已重置 {len(items)} 条记录的向量状态")
                
                # 3. 重新为所有条目生成向量
                logger.info("📝 步骤 3/3: 重新生成所有向量...")
                # 继续执行后续的向量化逻辑
            
            # 构建查询
            query = KnowledgeItem.query
            
            # 如果指定了ID列表，只处理这些条目
            if item_ids is not None and len(item_ids) > 0:
                query = query.filter(KnowledgeItem.id.in_(item_ids))
            
            # 如果仅处理未向量化的条目（rebuild_index时忽略此条件）
            if only_unprocessed and not force_resync and not rebuild_index:
                query = query.filter(
                    db.or_(
                        KnowledgeItem.vector_id.is_(None),
                        KnowledgeItem.status == 'pending'
                    )
                )
            
            items = query.all()
            
            if len(items) == 0:
                return {
                    'success': True,
                    'message': '没有需要同步的条目',
                    'total': 0,
                    'synced': 0,
                    'failed': 0,
                    'skipped': 0,
                    'errors': []
                }
            
            from Backend.services.vector_service import get_vector_service
            vector_service = get_vector_service()
            
            synced_count = 0
            failed_count = 0
            skipped_count = 0
            errors = []
            
            for item in items:
                try:
                    # 检查是否需要同步
                    if not force_resync and item.vector_id is not None:
                        skipped_count += 1
                        continue
                    
                    # 如果是强制重新同步，先删除旧向量并清空 vector_id
                    if force_resync and item.vector_id is not None:
                        old_vector_id = item.vector_id
                        try:
                            # 先将数据库中的 vector_id 设为 None，避免唯一性约束冲突
                            item.vector_id = None
                            db.session.flush()
                            # 然后删除向量映射
                            vector_service.delete_document(old_vector_id)
                            logger.info(f"删除旧向量 {old_vector_id} (强制重新同步)")
                        except Exception as e:
                            logger.warning(f"删除旧向量失败: {str(e)}")
                    
                    # 创建新向量
                    vector_id = vector_service.add_document(item.id, item.content)
                    
                    # 更新数据库
                    item.vector_id = vector_id
                    item.status = 'processed'
                    item.processed_at = datetime.now(timezone.utc)
                    
                    # 立即提交，避免批量操作时出现约束冲突
                    db.session.commit()
                    
                    synced_count += 1
                    logger.info(f"知识库条目 {item.id} 向量同步成功，vector_id: {vector_id}")
                    
                except Exception as e:
                    failed_count += 1
                    error_msg = f"ID {item.id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"条目 {item.id} 向量同步失败: {str(e)}")
                    # 回滚当前条目的更改
                    db.session.rollback()
            
            # 根据是否为重建模式生成不同的消息
            if rebuild_index:
                message = f'向量索引重建完成：成功 {synced_count} 条，失败 {failed_count} 条'
            else:
                message = f'批量同步完成：成功 {synced_count} 条，失败 {failed_count} 条，跳过 {skipped_count} 条'
            
            result = {
                'success': True,
                'message': message,
                'total': len(items),
                'synced': synced_count,
                'failed': failed_count,
                'skipped': skipped_count,
                'errors': errors,
                'rebuild_mode': rebuild_index
            }
            
            logger.info(f"批量向量同步完成: {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"批量向量同步失败: {str(e)}")
            raise ValueError(f'批量向量同步失败: {str(e)}')
