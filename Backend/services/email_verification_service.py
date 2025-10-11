"""
邮箱验证服务
"""
from datetime import datetime, timezone
from Backend.models import User, db
from Backend.models.email_verification import EmailVerificationToken
from Backend.services.email_service import EmailService
from flask import current_app


class EmailVerificationService:
    """邮箱验证服务"""
    
    @staticmethod
    def send_verification_email(user_id, email):
        """
        发送邮箱验证邮件
        
        Args:
            user_id: 用户ID
            email: 邮箱地址
            
        Returns:
            (是否成功, 消息)
        """
        try:
            # 查找用户
            user = db.session.get(User, user_id)
            if not user:
                return False, "用户不存在"
            
            # 创建验证令牌
            verification_token = EmailVerificationToken.create_token(user_id, email)
            
            # 生成验证链接
            frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
            verification_url = f"{frontend_url}/verify-email?token={verification_token.token}"
            
            # 发送验证邮件
            email_service = EmailService()
            success = email_service.send_email_verification(
                to_email=email,
                username=user.username,
                verification_token=verification_token.token,
                verification_url=verification_url
            )
            
            if success:
                return True, "验证邮件已发送，请检查您的邮箱"
            else:
                return False, "邮件发送失败，请稍后重试"
                
        except Exception as e:
            current_app.logger.error(f"发送验证邮件失败: {str(e)}")
            return False, "发送验证邮件失败，请稍后重试"
    
    @staticmethod
    def verify_email(token):
        """
        验证邮箱
        
        Args:
            token: 验证令牌
            
        Returns:
            (是否成功, 消息, 用户对象)
        """
        try:
            # 查找令牌
            verification_token = EmailVerificationToken.query.filter_by(token=token).first()
            if not verification_token:
                return False, "无效的验证令牌", None
            
            # 检查令牌是否有效
            if not verification_token.is_valid():
                return False, "验证令牌已过期或已被使用", None
            
            # 获取用户
            user = db.session.get(User, verification_token.user_id)
            if not user:
                return False, "用户不存在", None
            
            # 验证邮箱是否匹配
            if user.email != verification_token.email:
                return False, "邮箱地址不匹配", None
            
            # 标记邮箱为已验证
            user.is_email_verified = True
            
            # 标记令牌为已使用
            verification_token.use_token()
            
            # 提交更改
            db.session.commit()
            
            return True, "邮箱验证成功", user
            
        except Exception as e:
            current_app.logger.error(f"验证邮箱失败: {str(e)}")
            db.session.rollback()
            return False, "验证邮箱失败，请稍后重试", None
    
    @staticmethod
    def resend_verification_email(user_id):
        """
        重新发送验证邮件
        
        Args:
            user_id: 用户ID
            
        Returns:
            (是否成功, 消息)
        """
        try:
            # 查找用户
            user = db.session.get(User, user_id)
            if not user:
                return False, "用户不存在"
            
            if user.is_email_verified:
                return False, "邮箱已经验证过了"
            
            # 发送验证邮件
            return EmailVerificationService.send_verification_email(user_id, user.email)
            
        except Exception as e:
            current_app.logger.error(f"重新发送验证邮件失败: {str(e)}")
            return False, "重新发送验证邮件失败，请稍后重试"
    
    @staticmethod
    def cleanup_expired_tokens():
        """清理过期的验证令牌"""
        try:
            expired_tokens = EmailVerificationToken.query.filter(
                EmailVerificationToken.expires_at < datetime.now(timezone.utc)
            ).all()
            
            for token in expired_tokens:
                db.session.delete(token)
            
            db.session.commit()
            current_app.logger.info(f"清理了 {len(expired_tokens)} 个过期的邮箱验证令牌")
            
        except Exception as e:
            current_app.logger.error(f"清理过期令牌失败: {str(e)}")
            db.session.rollback()
    
    @staticmethod
    def check_verification_required(user):
        """
        检查是否需要邮箱验证
        
        Args:
            user: 用户对象
            
        Returns:
            是否需要验证
        """
        # 这里可以根据业务需求设置验证要求
        # 例如：新注册用户必须验证邮箱，或者所有用户都必须验证
        return not user.is_email_verified
