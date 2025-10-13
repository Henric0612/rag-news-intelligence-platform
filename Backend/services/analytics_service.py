"""
数据分析服务
提供知识库数据聚类分析和关键词提取功能
"""
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
import numpy as np
from Backend.models import KnowledgeItem, db
from Backend.utils.text_utils import clean_text
from Backend.services.keyword_service import get_keyword_service

logger = logging.getLogger(__name__)


class AnalyticsService:
    """数据分析服务类"""
    
    def __init__(self):
        """初始化分析服务"""
        pass
    
    def get_clustering_report(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        生成知识库聚类分析报告
        
        Args:
            limit: 限制分析的文档数量，None表示分析全部
            
        Returns:
            Dict: 包含Top10关键词和聚类分布的报告
        """
        try:
            # Check cache first (only if no limit specified - full dataset)
            if limit is None:
                from Backend.services.analytics_cache_service import AnalyticsCacheService
                cached_report = AnalyticsCacheService.get_cached_report()
                if cached_report:
                    logger.info("Using cached analytics report (knowledge base unchanged)")
                    return cached_report
            
            logger.info("开始生成聚类分析报告")
            
            # 1. 获取知识库数据
            query = KnowledgeItem.query.order_by(KnowledgeItem.created_at.desc())
            if limit:
                query = query.limit(limit)
            
            items = query.all()
            
            if not items:
                return {
                    'success': True,  # 空数据库是正常情况，不是错误
                    'message': '知识库中暂无数据',
                    'top_10_keywords': [],
                    'total_items': 0,
                    'total_keywords_extracted': 0,
                    'unique_keywords': 0,
                    'category_distribution': [],
                    'source_type_distribution': [],
                    'timestamp': None
                }
            
            logger.info(f"获取到 {len(items)} 条知识库数据")
            
            # 2. 使用 KeyBERT 提取高质量关键词
            # 初始化统计变量
            all_keywords = []
            keyword_freq = Counter()
            
            try:
                keyword_service = get_keyword_service()
                
                # 策略优化：从每篇文章分别提取关键词，然后统计频次
                # 这样能更好地反映整体主题而非个别文章的长句
                all_keywords = []
                
                for item in items:
                    # 准备文本：只使用标题（标题包含最核心的主题）
                    # 避免内容中的长句干扰
                    text = f"{item.title} {item.title} {item.title}"
                    
                    # 从每篇文章只提取2个最核心的关键词
                    item_keywords = keyword_service.extract_keywords_keybert(
                        texts=[text],
                        top_k=2,  # 减少到2个，确保只提取最核心的
                        diversity=0.9,  # 最高多样性
                        use_mmr=True
                    )
                    
                    # 收集关键词
                    if item_keywords:
                        all_keywords.extend([kw['keyword'] for kw in item_keywords])
                
                # 统计关键词频次
                keyword_freq = Counter(all_keywords)
                top_10 = keyword_freq.most_common(10)
                
                if top_10:
                    # 计算总频次用于百分比
                    total_count = sum(count for _, count in top_10)
                    
                    top_10_keywords = [
                        {
                            'keyword': keyword,
                            'count': count,
                            'percentage': round(count / total_count * 100, 2) if total_count > 0 else 0
                        }
                        for keyword, count in top_10
                    ]
                    
                    all_keywords = [kw for kw, _ in top_10]
                else:
                    top_10_keywords = []
                
                logger.info(f"✅ KeyBERT提取Top10关键词: {[k['keyword'] for k in top_10_keywords]}")
                
            except Exception as e:
                logger.error(f"❌ KeyBERT提取失败，使用降级方案: {str(e)}")
                # 降级到旧方法
                from Backend.utils.text_utils import extract_keywords
                all_keywords = []
                for item in items:
                    text = f"{item.title} {item.content}"
                    keywords = extract_keywords(text, top_k=20)
                    all_keywords.extend(keywords)
                
                keyword_freq = Counter(all_keywords)
                top_10 = keyword_freq.most_common(10)
                
                top_10_keywords = [
                    {
                        'keyword': keyword,
                        'count': count,
                        'percentage': round(count / len(all_keywords) * 100, 2) if all_keywords else 0
                    }
                    for keyword, count in top_10
                ]
                
                logger.info(f"降级方案Top10关键词: {[k['keyword'] for k in top_10_keywords]}")
            
            # 4. 按分类统计
            category_stats = self._get_category_statistics(items)
            
            # 5. 按来源类型统计
            source_type_stats = self._get_source_type_statistics(items)
            
            report = {
                'success': True,
                'top_10_keywords': top_10_keywords,
                'total_items': len(items),
                'total_keywords_extracted': len(all_keywords),
                'unique_keywords': len(keyword_freq),
                'category_distribution': category_stats,
                'source_type_distribution': source_type_stats,
                'timestamp': items[0].created_at.isoformat() if items else None
            }
            
            logger.info("聚类分析报告生成完成")
            
            # Cache the report (only if no limit - full dataset)
            if limit is None:
                from Backend.services.analytics_cache_service import AnalyticsCacheService
                AnalyticsCacheService.set_cached_report(report)
            
            return report
            
        except Exception as e:
            logger.error(f"生成聚类分析报告失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': '生成分析报告失败'
            }
    
    
    def _get_category_label(self, category: str) -> str:
        """获取分类的中文标签"""
        labels = {
            'politics': '政治',
            'economy': '经济',
            'technology': '科技',
            'society': '社会',
            'culture': '文化',
            'sports': '体育',
            'entertainment': '娱乐',
            'education': '教育',
            'health': '健康',
            'military': '军事'
        }
        return labels.get(category, category)
    
    def _get_category_statistics(self, items: List[KnowledgeItem]) -> List[Dict[str, Any]]:
        """统计各分类的文档数量"""
        try:
            category_counts = Counter(item.category if item.category else '未分类' for item in items)
            return [
                {
                    'category': category,
                    'count': count,
                    'percentage': round(count / len(items) * 100, 2)
                }
                for category, count in category_counts.most_common()
            ]
        except Exception as e:
            logger.error(f"统计分类失败: {str(e)}")
            return []
    
    def _get_source_type_statistics(self, items: List[KnowledgeItem]) -> List[Dict[str, Any]]:
        """统计各来源类型的文档数量"""
        try:
            source_counts = Counter(item.source_type for item in items)
            return [
                {
                    'source_type': source_type,
                    'count': count,
                    'percentage': round(count / len(items) * 100, 2)
                }
                for source_type, count in source_counts.most_common()
            ]
        except Exception as e:
            logger.error(f"统计来源类型失败: {str(e)}")
            return []
    
    def get_trend_analysis(self, days: int = 30) -> Dict[str, Any]:
        """
        获取趋势分析数据
        
        Args:
            days: 分析的天数
            
        Returns:
            Dict: 趋势分析结果
        """
        try:
            from datetime import datetime, timedelta, timezone
            
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # 按天统计
            items = KnowledgeItem.query.filter(
                KnowledgeItem.created_at >= start_date
            ).all()
            
            daily_counts = {}
            for item in items:
                day_key = item.created_at.strftime('%Y-%m-%d')
                daily_counts[day_key] = daily_counts.get(day_key, 0) + 1
            
            # 填充缺失的日期
            current_date = start_date
            trend_data = []
            while current_date <= end_date:
                day_key = current_date.strftime('%Y-%m-%d')
                trend_data.append({
                    'date': day_key,
                    'count': daily_counts.get(day_key, 0)
                })
                current_date += timedelta(days=1)
            
            return {
                'success': True,
                'days': days,
                'total_items': len(items),
                'trend_data': trend_data,
                'average_per_day': round(len(items) / days, 2) if days > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"趋势分析失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            total_items = KnowledgeItem.query.count()
            return {
                'status': 'healthy',
                'total_items': total_items,
                'service': 'analytics'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'service': 'analytics'
            }


# 全局分析服务实例
_analytics_service = None


def get_analytics_service() -> AnalyticsService:
    """获取分析服务实例（单例模式）"""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service

