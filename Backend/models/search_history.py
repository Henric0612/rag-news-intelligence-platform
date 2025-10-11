"""
搜索历史模型
"""
from datetime import datetime, timezone
from . import db


class SearchHistory(db.Model):
    """搜索历史表"""
    __tablename__ = 'search_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_id = db.Column(db.String(100))
    
    # 搜索内容
    query = db.Column(db.Text, nullable=False)
    query_type = db.Column(db.String(20), default='semantic')  # 'semantic', 'keyword', 'hybrid'
    filters = db.Column(db.JSON)
    
    # 搜索结果
    results_count = db.Column(db.Integer, default=0)
    top_results = db.Column(db.JSON)
    
    # 性能指标
    response_time = db.Column(db.Float)
    retrieval_time = db.Column(db.Float)
    generation_time = db.Column(db.Float)
    
    # 用户反馈
    satisfaction_score = db.Column(db.Integer)
    feedback_text = db.Column(db.Text)
    clicked_results = db.Column(db.JSON)
    
    # 时间记录
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
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
            'user_id': self.user_id,
            'query': self.query,
            'query_type': self.query_type,
            'results_count': self.results_count,
            'response_time': self.response_time,
            'created_at': format_datetime(self.created_at)
        }
    
    def __repr__(self):
        return f'<SearchHistory {self.query[:30]}>'
