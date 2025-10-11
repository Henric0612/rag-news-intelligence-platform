"""
邮箱验证模型
"""
from datetime import datetime, timezone, timedelta
from . import db
import secrets
import string


class EmailVerificationToken(db.Model):
    """邮箱验证令牌表"""
    __tablename__ = 'email_verification_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # 关系
    user = db.relationship('User', backref='email_verification_tokens')
    
    @staticmethod
    def generate_token():
        """生成验证令牌"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    @staticmethod
    def create_token(user_id, email, expires_hours=24):
        """创建邮箱验证令牌"""
        # 使该用户的所有旧令牌失效
        EmailVerificationToken.query.filter_by(user_id=user_id, used=False).update({'used': True})
        
        # 创建新令牌
        token = EmailVerificationToken(
            user_id=user_id,
            email=email,
            token=EmailVerificationToken.generate_token(),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_hours)
        )
        
        db.session.add(token)
        db.session.commit()
        
        return token
    
    def is_valid(self):
        """检查令牌是否有效"""
        now = datetime.now(timezone.utc)
        # 如果expires_at没有时区信息，添加UTC时区
        if self.expires_at.tzinfo is None:
            expires_at_utc = self.expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at_utc = self.expires_at
        return not self.used and expires_at_utc > now
    
    def use_token(self):
        """使用令牌（标记为已使用）"""
        self.used = True
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
            'email': self.email,
            'token': self.token,
            'expires_at': format_datetime(self.expires_at),
            'used': self.used,
            'created_at': format_datetime(self.created_at)
        }
    
    def __repr__(self):
        return f'<EmailVerificationToken {self.email} - {self.token[:8]}...>'
