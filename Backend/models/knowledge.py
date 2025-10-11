"""
知识库模型
"""
from datetime import datetime, timezone
from . import db


class KnowledgeItem(db.Model):
    """知识库数据表"""
    __tablename__ = 'knowledge_items'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    source_url = db.Column(db.String(500))
    source_name = db.Column(db.String(100))
    source_type = db.Column(db.String(50), nullable=False)  # 'rss', 'web', 'upload', 'manual'
    category = db.Column(db.String(100), index=True)
    tags = db.Column(db.JSON)
    language = db.Column(db.String(10), default='zh')
    markdown_content = db.Column(db.Text)
    
    # 向量化相关
    vector_id = db.Column(db.String(100), unique=True)
    content_hash = db.Column(db.String(64), unique=True, index=True)
    embedding_model = db.Column(db.String(100), default='all-MiniLM-L6-v2')
    
    # 质量和状态
    quality_score = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'processed', 'published', 'archived'
    
    # 时间字段
    published_at = db.Column(db.DateTime, index=True)
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self, include_content=True):
        """转换为字典"""
        def format_datetime(dt):
            """将naive datetime转换为UTC ISO格式字符串"""
            if dt is None:
                return None
            # 如果datetime没有时区信息，假定它是UTC时间并添加时区标识
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        
        # 根据quality_score计算quality_level
        quality_level = self._get_quality_level(self.quality_score)
        
        data = {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'source_url': self.source_url,
            'source_name': self.source_name,
            'source_type': self.source_type,
            'category': self.category,
            'tags': self.tags,
            'language': self.language,
            'vector_id': self.vector_id,  # 添加向量ID
            'is_vectorized': self.vector_id is not None,  # 添加是否已向量化标志
            'quality_score': self.quality_score,
            'quality_level': quality_level,  # 添加质量等级
            'status': self.status,
            'published_at': format_datetime(self.published_at),
            'created_at': format_datetime(self.created_at)
        }
        
        if include_content:
            data['content'] = self.content
            data['markdown_content'] = self.markdown_content
        
        return data
    
    def _get_quality_level(self, quality_score):
        """根据质量评分获取质量等级"""
        if quality_score >= 80:
            return 'excellent'
        elif quality_score >= 60:
            return 'good'
        elif quality_score >= 40:
            return 'fair'
        else:
            return 'poor'
    
    def __repr__(self):
        return f'<KnowledgeItem {self.title}>'
