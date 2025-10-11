"""
密码重置服务
"""
from datetime import datetime, timezone
from Backend.models import User, db
from Backend.models.password_reset import PasswordResetToken
from Backend.services.email_service import EmailService
from Backend.utils.text_utils import validate_password_strength
from flask import current_app


class PasswordResetService:
    """密码重置服务"""
    
    @staticmethod
    def request_password_reset(email: str) -> tuple[bool, str]:
        """
        请求密码重置
        
        Args:
            email: 用户邮箱
            
        Returns:
            (是否成功, 消息)
        """
        try:
            # 查找用户
            user = User.query.filter_by(email=email).first()
            if not user:
                # 为了安全，即使用户不存在也返回成功消息
                return True, "如果该邮箱已注册，您将收到密码重置邮件"
            
            if not user.is_active:
                return False, "账户已被禁用，无法重置密码"
            
            # 创建重置令牌
            reset_token = PasswordResetToken.create_token(user.id)
            
            # 生成重置链接
            frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
            reset_url = f"{frontend_url}/reset-password?token={reset_token.token}"
            
            # 发送重置邮件
            email_service = EmailService()
            success = email_service.send_password_reset_email(
                to_email=user.email,
                username=user.username,
                reset_token=reset_token.token,
                reset_url=reset_url
            )
            
            if success:
                return True, "密码重置邮件已发送，请检查您的邮箱"
            else:
                return False, "邮件发送失败，请稍后重试"
                
        except Exception as e:
            current_app.logger.error(f"密码重置请求失败: {str(e)}")
            return False, "密码重置请求失败，请稍后重试"
    
    @staticmethod
    def verify_reset_token(token: str) -> tuple[bool, str, User]:
        """
        验证重置令牌
        
        Args:
            token: 重置令牌
            
        Returns:
            (是否有效, 消息, 用户对象)
        """
        try:
            # 查找令牌
            reset_token = PasswordResetToken.query.filter_by(token=token).first()
            if not reset_token:
                return False, "无效的重置令牌", None
            
            # 检查令牌是否有效
            if not reset_token.is_valid():
                return False, "重置令牌已过期或已被使用", None
            
            # 获取用户
            user = db.session.get(User, reset_token.user_id)
            if not user or not user.is_active:
                return False, "用户不存在或已被禁用", None
            
            return True, "令牌有效", user
            
        except Exception as e:
            current_app.logger.error(f"验证重置令牌失败: {str(e)}")
            return False, "验证令牌失败", None
    
    @staticmethod
    def reset_password(token: str, new_password: str) -> tuple[bool, str]:
        """
        重置密码
        
        Args:
            token: 重置令牌
            new_password: 新密码
            
        Returns:
            (是否成功, 消息)
        """
        try:
            # 验证密码强度
            is_valid, error_msg = validate_password_strength(new_password)
            if not is_valid:
                return False, error_msg
            
            # 验证令牌
            is_valid_token, message, user = PasswordResetService.verify_reset_token(token)
            if not is_valid_token:
                return False, message
            
            # 更新密码
            user.set_password(new_password)
            
            # 标记令牌为已使用
            reset_token = PasswordResetToken.query.filter_by(token=token).first()
            reset_token.use_token()
            
            # 提交更改
            db.session.commit()
            
            return True, "密码重置成功"
            
        except Exception as e:
            current_app.logger.error(f"重置密码失败: {str(e)}")
            db.session.rollback()
            return False, "密码重置失败，请稍后重试"
    
    @staticmethod
    def cleanup_expired_tokens():
        """清理过期的重置令牌"""
        try:
            expired_tokens = PasswordResetToken.query.filter(
                PasswordResetToken.expires_at < datetime.now(timezone.utc)
            ).all()
            
            for token in expired_tokens:
                db.session.delete(token)
            
            db.session.commit()
            current_app.logger.info(f"清理了 {len(expired_tokens)} 个过期的重置令牌")
            
        except Exception as e:
            current_app.logger.error(f"清理过期令牌失败: {str(e)}")
            db.session.rollback()
