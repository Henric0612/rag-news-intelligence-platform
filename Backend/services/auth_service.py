"""
认证服务
"""
from datetime import datetime, timezone
from flask import request, current_app
from Backend.models import User, db
from Backend.utils.jwt_utils import create_access_token, create_refresh_token
from Backend.utils.text_utils import validate_password_strength, validate_email_format
from Backend.services.account_security_service import AccountSecurityService
from Backend.services.email_verification_service import EmailVerificationService


class AuthService:
    """用户认证服务"""
    
    @staticmethod
    def register_user(username, password, email):
        """注册用户"""
        # 验证邮箱格式
        is_valid_email, email_error = validate_email_format(email)
        if not is_valid_email:
            raise ValueError(email_error)
        
        # 验证密码强度
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            raise ValueError('用户名已存在')
        
        # 检查邮箱是否已存在
        if User.query.filter_by(email=email).first():
            raise ValueError('邮箱已被注册')
        
        # 创建新用户
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # 发送邮箱验证邮件
        try:
            EmailVerificationService.send_verification_email(user.id, email)
        except Exception as e:
            # 验证邮件发送失败不影响注册流程
            current_app.logger.warning(f"发送验证邮件失败: {str(e)}")
        
        return user
    
    @staticmethod
    def authenticate_user(username, password):
        """验证用户登录（支持用户名或邮箱登录）"""
        # 获取客户端信息
        ip_address = request.remote_addr or 'unknown'
        user_agent = request.headers.get('User-Agent', 'unknown')
        
        # 先尝试按用户名查找
        user = User.query.filter_by(username=username).first()
        
        # 如果用户名没找到，尝试按邮箱查找
        if not user:
            user = User.query.filter_by(email=username).first()
        
        # 验证用户和密码
        if not user or not user.check_password(password):
            # 记录失败的登录尝试
            AccountSecurityService.log_login_attempt(
                user_id=user.id if user else None,
                username=username,
                email=user.email if user else None,
                ip_address=ip_address,
                user_agent=user_agent,
                login_type='failed',
                failure_reason='用户名或密码错误'
            )
            
            raise ValueError('用户名或密码错误')
        
        if not user.is_active:
            # 记录被禁用的登录尝试
            AccountSecurityService.log_login_attempt(
                user_id=user.id,
                username=username,
                email=user.email,
                ip_address=ip_address,
                user_agent=user_agent,
                login_type='blocked',
                failure_reason='账户已被禁用'
            )
            raise ValueError('账户已被禁用')
        
        # 记录成功的登录
        AccountSecurityService.log_login_attempt(
            user_id=user.id,
            username=username,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
            login_type='success'
        )
        
        # 更新最后登录时间（时区感知）
        user.last_login_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return user
    
    @staticmethod
    def generate_tokens(user_id):
        """生成访问令牌和刷新令牌（包含过期时间）"""
        from flask import current_app
        
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        
        # ✅ 获取token过期时间（秒）
        access_token_expires_in = int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
        refresh_token_expires_in = int(current_app.config['JWT_REFRESH_TOKEN_EXPIRES'].total_seconds())
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': access_token_expires_in,  # ✅ Access Token过期时间（秒）
            'refresh_expires_in': refresh_token_expires_in  # ✅ Refresh Token过期时间（秒）
        }
    
    @staticmethod
    def get_user_by_id(user_id):
        """通过ID获取用户"""
        return db.session.get(User, user_id)
