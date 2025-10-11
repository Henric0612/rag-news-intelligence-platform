"""
用户模型
"""
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class User(db.Model):
    """用户表"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), default='user')  # 'admin' or 'user'
    is_active = db.Column(db.Boolean, default=True)
    is_email_verified = db.Column(db.Boolean, default=False)
    avatar_url = db.Column(db.String(255))
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # 关系
    search_histories = db.relationship('SearchHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
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
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'is_email_verified': self.is_email_verified,
            'avatar_url': self.avatar_url,
            'last_login_at': format_datetime(self.last_login_at),
            'created_at': format_datetime(self.created_at)
        }
    
    def __repr__(self):
        return f'<User {self.username}>'
