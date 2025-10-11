"""
数据分析服务
提供知识库数据聚类分析和关键词提取功能
"""
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
import numpy as np
from Backend.models import KnowledgeItem, db
from Backend.utils.text_utils import extract_keywords, clean_text

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
            
            # 2. 提取所有文档的关键词
            all_keywords = []
            for item in items:
                # 合并标题和内容
                text = f"{item.title} {item.content}"
                keywords = extract_keywords(text, top_k=20)
                all_keywords.extend(keywords)
            
            # 3. 统计关键词频次，获取Top10
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
            
            logger.info(f"Top10关键词: {[k['keyword'] for k in top_10_keywords]}")
            
            # 4. 尝试进行KMeans聚类（如果数据足够多）
            cluster_info = None
            if len(items) >= 5:
                try:
                    cluster_info = self._perform_clustering(items)
                except Exception as e:
                    logger.warning(f"聚类分析失败: {str(e)}")
            
            # 5. 按分类统计
            category_stats = self._get_category_statistics(items)
            
            # 6. 按来源类型统计
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
            
            if cluster_info:
                report['clustering'] = cluster_info
            
            logger.info("聚类分析报告生成完成")
            return report
            
        except Exception as e:
            logger.error(f"生成聚类分析报告失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': '生成分析报告失败'
            }
    
    def _perform_clustering(self, items: List[KnowledgeItem], n_clusters: int = 5) -> Dict[str, Any]:
        """
        执行KMeans聚类分析
        
        Args:
            items: 知识库条目列表
            n_clusters: 聚类数量
            
        Returns:
            Dict: 聚类结果
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.cluster import KMeans
            
            # 准备文本数据
            texts = [f"{item.title} {item.content[:500]}" for item in items]
            
            # 调整聚类数量（不能超过文档数量）
            n_clusters = min(n_clusters, len(items))
            
            # TF-IDF向量化
            vectorizer = TfidfVectorizer(
                max_features=100,
                max_df=0.8,
                min_df=2,
                ngram_range=(1, 2)
            )
            X = vectorizer.fit_transform(texts)
            
            # KMeans聚类
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X)
            
            # 统计每个聚类的文档数量
            cluster_counts = Counter(clusters)
            cluster_distribution = [
                {
                    'cluster_id': int(cluster_id),
                    'count': count,
                    'percentage': round(count / len(items) * 100, 2)
                }
                for cluster_id, count in sorted(cluster_counts.items())
            ]
            
            # 提取每个聚类的代表性关键词
            feature_names = vectorizer.get_feature_names_out()
            cluster_keywords = {}
            
            for i in range(n_clusters):
                # 获取该聚类的中心点
                center = kmeans.cluster_centers_[i]
                # 获取权重最高的前5个特征
                top_indices = center.argsort()[-5:][::-1]
                keywords = [feature_names[idx] for idx in top_indices]
                cluster_keywords[f'cluster_{i}'] = keywords
            
            return {
                'n_clusters': n_clusters,
                'distribution': cluster_distribution,
                'cluster_keywords': cluster_keywords,
                'method': 'KMeans'
            }
            
        except ImportError:
            logger.warning("scikit-learn未安装，跳过聚类分析")
            return None
        except Exception as e:
            logger.error(f"KMeans聚类失败: {str(e)}")
            raise
    
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

