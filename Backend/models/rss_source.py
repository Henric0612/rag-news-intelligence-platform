"""
RSS订阅源模型
"""
from datetime import datetime, timezone
from . import db


def _get_utc_now():
    """获取当前UTC时间（用于数据库默认值）"""
    return datetime.now(timezone.utc)


class RSSSource(db.Model):
    """RSS订阅源表"""
    __tablename__ = 'rss_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), unique=True, nullable=False)
    category = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True, index=True)
    last_crawled = db.Column(db.DateTime)
    crawl_frequency = db.Column(db.Integer, default=3600)  # 秒
    created_at = db.Column(db.DateTime, default=_get_utc_now)
    
    # 关系
    crawl_tasks = db.relationship('CrawlTask', backref='rss_source', lazy='dynamic')
    
    def to_dict(self):
        """转换为字典"""
        def format_datetime(dt):
            """将naive datetime转换为UTC ISO格式字符串"""
            if dt is None:
                return None
            # 如果datetime没有时区信息，假定它是UTC时间并添加时区标识
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'category': self.category,
            'is_active': self.is_active,
            'last_crawled': format_datetime(self.last_crawled),
            'crawl_frequency': self.crawl_frequency,
            'created_at': format_datetime(self.created_at),
            'crawl_tasks_count': self.crawl_tasks.count()
        }
    
    def __repr__(self):
        return f'<RSSSource {self.name}>'
