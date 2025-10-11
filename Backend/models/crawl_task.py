"""
爬取任务模型
"""
from datetime import datetime, timezone
from . import db


def _get_utc_now():
    """获取当前UTC时间（用于数据库默认值）"""
    return datetime.now(timezone.utc)


class CrawlTask(db.Model):
    """爬取任务表"""
    __tablename__ = 'crawl_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('rss_sources.id'), nullable=True)  # Web抓取时为NULL
    task_type = db.Column(db.String(50), nullable=False)  # 'rss', 'web', 'scheduled'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'running', 'completed', 'failed'
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    items_crawled = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_get_utc_now)
    
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
            'source_id': self.source_id,
            'task_type': self.task_type,
            'status': self.status,
            'started_at': format_datetime(self.started_at),
            'completed_at': format_datetime(self.completed_at),
            'items_crawled': self.items_crawled,
            'error_message': self.error_message,
            'created_at': format_datetime(self.created_at)
        }
    
    def __repr__(self):
        return f'<CrawlTask {self.id} - {self.status}>'
