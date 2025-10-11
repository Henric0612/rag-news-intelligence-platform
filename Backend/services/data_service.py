"""
数据管理服务 - 负责数据源管理和批量处理
"""
import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from sqlalchemy.exc import SQLAlchemyError

from ..models import db, RSSSource, CrawlTask, KnowledgeItem
from ..services.crawler_service import CrawlerService
from ..services.file_service import FileService
from ..services.knowledge_service import KnowledgeService
from ..services.vector_service import VectorService

logger = logging.getLogger(__name__)


class DataService:
    """数据管理服务类"""
    
    def __init__(self):
        self.crawler_service = CrawlerService()
        self.file_service = FileService()
        self.knowledge_service = KnowledgeService()
        self.vector_service = VectorService()
    
    def manage_data_sources(self) -> Dict[str, Any]:
        """
        管理数据源 - 获取所有数据源的统计信息
        
        Returns:
            Dict: 数据源管理信息
        """
        try:
            # RSS源统计
            rss_stats = self._get_rss_source_stats()
            
            # 知识库统计
            knowledge_stats = self._get_knowledge_stats()
            
            # 爬取任务统计
            task_stats = self._get_crawl_task_stats()
            
            # 文件上传统计
            file_stats = self._get_file_stats()
            
            return {
                'success': True,
                'data_sources': {
                    'rss_sources': rss_stats,
                    'knowledge_items': knowledge_stats,
                    'crawl_tasks': task_stats,
                    'uploaded_files': file_stats
                },
                'total_data_items': knowledge_stats['total_items'],
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取数据源管理信息失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def monitor_crawl_tasks(self, limit: int = 50) -> Dict[str, Any]:
        """
        监控爬取任务
        
        Args:
            limit: 返回任务数量限制
            
        Returns:
            Dict: 爬取任务监控信息
        """
        try:
            # 获取最近的任务
            recent_tasks = CrawlTask.query.order_by(
                CrawlTask.created_at.desc()
            ).limit(limit).all()
            
            tasks_data = []
            for task in recent_tasks:
                task_data = task.to_dict()
                if task.rss_source:
                    task_data['source_name'] = task.rss_source.name
                    task_data['source_url'] = task.rss_source.url
                else:
                    task_data['source_name'] = 'Unknown'
                    task_data['source_url'] = 'Unknown'
                tasks_data.append(task_data)
            
            # 获取任务统计
            total_tasks = CrawlTask.query.count()
            pending_tasks = CrawlTask.query.filter_by(status='pending').count()
            running_tasks = CrawlTask.query.filter_by(status='running').count()
            completed_tasks = CrawlTask.query.filter_by(status='completed').count()
            failed_tasks = CrawlTask.query.filter_by(status='failed').count()
            
            # 最近24小时的任务
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            recent_24h = CrawlTask.query.filter(
                CrawlTask.created_at >= yesterday
            ).count()
            
            return {
                'success': True,
                'tasks': tasks_data,
                'statistics': {
                    'total': total_tasks,
                    'pending': pending_tasks,
                    'running': running_tasks,
                    'completed': completed_tasks,
                    'failed': failed_tasks,
                    'recent_24h': recent_24h
                }
            }
            
        except Exception as e:
            logger.error(f"监控爬取任务失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_data_quality(self, data_type: str = 'all') -> Dict[str, Any]:
        """
        检查数据质量
        
        Args:
            data_type: 数据类型 ('all', 'rss', 'web', 'upload')
            
        Returns:
            Dict: 数据质量检查结果
        """
        try:
            quality_issues = []
            
            # 检查知识库数据
            knowledge_items = KnowledgeItem.query.all()
            if data_type != 'all' and data_type in ['rss', 'web', 'upload']:
                knowledge_items = KnowledgeItem.query.filter_by(source_type=data_type).all()
            
            total_items = len(knowledge_items)
            issues_count = 0
            
            for item in knowledge_items:
                item_issues = []
                
                # 检查标题
                if not item.title or len(item.title.strip()) < 3:
                    item_issues.append('标题过短或为空')
                
                # 检查内容
                if not item.content or len(item.content.strip()) < 10:
                    item_issues.append('内容过短或为空')
                
                # 检查向量ID
                if not item.vector_id:
                    item_issues.append('缺少向量ID')
                
                # 检查重复内容
                duplicate_content = KnowledgeItem.query.filter(
                    KnowledgeItem.content == item.content,
                    KnowledgeItem.id != item.id
                ).first()
                if duplicate_content:
                    item_issues.append('内容重复')
                
                if item_issues:
                    issues_count += 1
                    quality_issues.append({
                        'id': item.id,
                        'title': item.title,
                        'source_type': item.source_type,
                        'issues': item_issues
                    })
            
            # 计算质量分数
            quality_score = max(0, (total_items - issues_count) / total_items * 100) if total_items > 0 else 100
            
            return {
                'success': True,
                'quality_score': round(quality_score, 2),
                'total_items': total_items,
                'issues_count': issues_count,
                'quality_issues': quality_issues[:100],  # 限制返回数量
                'data_type': data_type
            }
            
        except Exception as e:
            logger.error(f"检查数据质量失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def batch_process_data(self, operation: str, data_ids: List[int], **kwargs) -> Dict[str, Any]:
        """
        批量处理数据
        
        Args:
            operation: 操作类型 ('delete', 'revectorize', 'categorize', 'tag')
            data_ids: 数据ID列表
            **kwargs: 额外参数
            
        Returns:
            Dict: 批量处理结果
        """
        try:
            if not data_ids:
                return {
                    'success': False,
                    'error': '没有指定要处理的数据'
                }
            
            processed_count = 0
            failed_count = 0
            errors = []
            
            for data_id in data_ids:
                try:
                    item = db.session.get(KnowledgeItem, data_id)
                    if not item:
                        failed_count += 1
                        errors.append(f"ID {data_id} 的数据不存在")
                        continue
                    
                    if operation == 'delete':
                        result = self._delete_data_item(item)
                    elif operation == 'revectorize':
                        result = self._revectorize_data_item(item)
                    elif operation == 'categorize':
                        category = kwargs.get('category')
                        result = self._categorize_data_item(item, category)
                    elif operation == 'tag':
                        tags = kwargs.get('tags', [])
                        result = self._tag_data_item(item, tags)
                    else:
                        failed_count += 1
                        errors.append(f"不支持的操作: {operation}")
                        continue
                    
                    if result['success']:
                        processed_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"ID {data_id}: {result['error']}")
                        
                except Exception as e:
                    failed_count += 1
                    errors.append(f"ID {data_id}: {str(e)}")
            
            return {
                'success': True,
                'operation': operation,
                'total_items': len(data_ids),
                'processed_count': processed_count,
                'failed_count': failed_count,
                'errors': errors[:10]  # 限制错误信息数量
            }
            
        except Exception as e:
            logger.error(f"批量处理数据失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_data(self, data_type: str = 'all', format: str = 'json') -> Dict[str, Any]:
        """
        导出数据
        
        Args:
            data_type: 数据类型 ('all', 'rss', 'web', 'upload')
            format: 导出格式 ('json', 'csv')
            
        Returns:
            Dict: 导出结果
        """
        try:
            # 获取数据
            query = KnowledgeItem.query
            if data_type != 'all' and data_type in ['rss', 'web', 'upload']:
                query = query.filter_by(source_type=data_type)
            
            items = query.all()
            
            if format == 'json':
                data = [item.to_dict() for item in items]
            elif format == 'csv':
                # 简化的CSV导出
                data = []
                for item in items:
                    data.append({
                        'id': item.id,
                        'title': item.title,
                        'content': item.content[:500] + '...' if len(item.content) > 500 else item.content,
                        'source_type': item.source_type,
                        'category': item.category,
                        'created_at': item.created_at.isoformat()
                    })
            else:
                return {
                    'success': False,
                    'error': f'不支持的导出格式: {format}'
                }
            
            return {
                'success': True,
                'data_type': data_type,
                'format': format,
                'count': len(items),
                'data': data
            }
            
        except Exception as e:
            logger.error(f"导出数据失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_rss_source_stats(self) -> Dict[str, Any]:
        """获取RSS源统计信息"""
        total_sources = RSSSource.query.count()
        active_sources = RSSSource.query.filter_by(is_active=True).count()
        
        # 最近7天有爬取活动的源
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_sources = RSSSource.query.filter(
            RSSSource.last_crawled >= week_ago
        ).count()
        
        return {
            'total': total_sources,
            'active': active_sources,
            'inactive': total_sources - active_sources,
            'recent_activity': recent_sources
        }
    
    def _get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        total_items = KnowledgeItem.query.count()
        rss_items = KnowledgeItem.query.filter_by(source_type='rss').count()
        web_items = KnowledgeItem.query.filter_by(source_type='web').count()
        upload_items = KnowledgeItem.query.filter_by(source_type='upload').count()
        
        # 有向量ID的项目
        vectorized_items = KnowledgeItem.query.filter(
            KnowledgeItem.vector_id.isnot(None)
        ).count()
        
        return {
            'total_items': total_items,
            'rss': rss_items,
            'web': web_items,
            'upload': upload_items,
            'vectorized': vectorized_items,
            'not_vectorized': total_items - vectorized_items
        }
    
    def _get_crawl_task_stats(self) -> Dict[str, Any]:
        """获取爬取任务统计信息"""
        total_tasks = CrawlTask.query.count()
        completed_tasks = CrawlTask.query.filter_by(status='completed').count()
        failed_tasks = CrawlTask.query.filter_by(status='failed').count()
        
        # 最近7天的任务
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_tasks = CrawlTask.query.filter(
            CrawlTask.created_at >= week_ago
        ).count()
        
        return {
            'total': total_tasks,
            'completed': completed_tasks,
            'failed': failed_tasks,
            'recent_week': recent_tasks
        }
    
    def _get_file_stats(self) -> Dict[str, Any]:
        """获取文件上传统计信息"""
        uploaded_items = KnowledgeItem.query.filter_by(source_type='upload').all()
        
        files_info = {}
        for item in uploaded_items:
            source_name = item.source_name
            if source_name not in files_info:
                files_info[source_name] = {
                    'filename': source_name,
                    'chunks_count': 0,
                    'total_size': 0
                }
            files_info[source_name]['chunks_count'] += 1
            files_info[source_name]['total_size'] += len(item.content)
        
        return {
            'total_files': len(files_info),
            'total_chunks': len(uploaded_items),
            'files': list(files_info.values())
        }
    
    def _delete_data_item(self, item: KnowledgeItem) -> Dict[str, Any]:
        """删除数据项"""
        try:
            # 从向量数据库删除
            if item.vector_id:
                try:
                    self.vector_service.delete_document(item.vector_id)
                except Exception as e:
                    logger.error(f"删除向量数据失败: {str(e)}")
            
            db.session.delete(item)
            db.session.commit()
            
            return {'success': True}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def _revectorize_data_item(self, item: KnowledgeItem) -> Dict[str, Any]:
        """重新向量化数据项"""
        try:
            # 删除旧的向量数据
            if item.vector_id:
                try:
                    self.vector_service.delete_document(item.vector_id)
                except Exception as e:
                    logger.error(f"删除旧向量数据失败: {str(e)}")
            
            # 重新向量化
            vector_id = self.vector_service.add_document(
                item.id,
                item.title + ' ' + item.content
            )
            item.vector_id = vector_id
            db.session.commit()
            
            return {'success': True}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def _categorize_data_item(self, item: KnowledgeItem, category: str) -> Dict[str, Any]:
        """给数据项分类"""
        try:
            item.category = category
            db.session.commit()
            return {'success': True}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def _tag_data_item(self, item: KnowledgeItem, tags: List[str]) -> Dict[str, Any]:
        """给数据项添加标签"""
        try:
            if not item.tags:
                item.tags = tags
            else:
                existing_tags = set(item.tags)
                new_tags = set(tags)
                item.tags = list(existing_tags.union(new_tags))
            
            db.session.commit()
            return {'success': True}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
