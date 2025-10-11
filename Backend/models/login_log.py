"""
登录日志模型
"""
from datetime import datetime, timezone
from . import db
from sqlalchemy import Index


class LoginLog(db.Model):
    """登录日志表"""
    __tablename__ = 'login_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 可以为空，记录失败登录
    username = db.Column(db.String(50), nullable=False, index=True)  # 记录尝试登录的用户名
    email = db.Column(db.String(100), nullable=True)  # 记录尝试登录的邮箱
    ip_address = db.Column(db.String(45), nullable=False)  # 支持IPv6
    user_agent = db.Column(db.Text, nullable=True)
    login_type = db.Column(db.String(20), nullable=False)  # 'success', 'failed', 'blocked'
    failure_reason = db.Column(db.String(100), nullable=True)  # 失败原因
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # 关系
    user = db.relationship('User', backref='login_logs')
    
    # 索引
    __table_args__ = (
        Index('idx_login_logs_user_id_created_at', 'user_id', 'created_at'),
        Index('idx_login_logs_ip_created_at', 'ip_address', 'created_at'),
        Index('idx_login_logs_username_created_at', 'username', 'created_at'),
    )
    
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
            'username': self.username,
            'email': self.email,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'login_type': self.login_type,
            'failure_reason': self.failure_reason,
            'created_at': format_datetime(self.created_at)
        }
    
    def __repr__(self):
        return f'<LoginLog {self.username} - {self.login_type}>'


class AccountLock(db.Model):
    """账户锁定表"""
    __tablename__ = 'account_locks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(50), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    lock_type = db.Column(db.String(20), nullable=False)  # 'user', 'ip', 'both'
    reason = db.Column(db.String(100), nullable=False)
    locked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # 关系
    user = db.relationship('User', backref='account_locks')
    
    def is_expired(self):
        """检查锁定是否已过期"""
        now = datetime.now(timezone.utc)
        # 如果expires_at没有时区信息，添加UTC时区
        if self.expires_at.tzinfo is None:
            expires_at_utc = self.expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at_utc = self.expires_at
        return now > expires_at_utc
    
    def is_valid(self):
        """检查锁定是否有效"""
        return self.is_active and not self.is_expired()
    
    def unlock(self):
        """解锁账户"""
        self.is_active = False
        db.session.commit()
    
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
            'username': self.username,
            'ip_address': self.ip_address,
            'lock_type': self.lock_type,
            'reason': self.reason,
            'locked_at': format_datetime(self.locked_at),
            'expires_at': format_datetime(self.expires_at),
            'is_active': self.is_active,
            'created_at': format_datetime(self.created_at)
        }
    
    def __repr__(self):
        return f'<AccountLock {self.username} - {self.lock_type}>'
