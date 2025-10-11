"""
账户安全服务
"""
from datetime import datetime, timezone, timedelta
from flask import request
from Backend.models import User, db
from Backend.models.login_log import LoginLog, AccountLock
from flask import current_app


class AccountSecurityService:
    """账户安全服务"""
    
    # 安全配置
    MAX_LOGIN_ATTEMPTS = 5  # 最大登录尝试次数
    LOCK_DURATION_HOURS = 24  # 锁定持续时间（小时）
    IP_MAX_ATTEMPTS = 10  # IP最大尝试次数
    IP_LOCK_DURATION_HOURS = 48  # IP锁定持续时间（小时）
    
    @staticmethod
    def log_login_attempt(user_id, username, email, ip_address, user_agent, 
                          login_type, failure_reason=None):
        """
        记录登录尝试
        
        Args:
            user_id: 用户ID（成功时）
            username: 用户名
            email: 邮箱（可选）
            ip_address: IP地址
            user_agent: 用户代理
            login_type: 登录类型 ('success', 'failed', 'blocked')
            failure_reason: 失败原因
        """
        try:
            log = LoginLog(
                user_id=user_id,
                username=username,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                login_type=login_type,
                failure_reason=failure_reason
            )
            
            db.session.add(log)
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"记录登录日志失败: {str(e)}")
            db.session.rollback()
    
    @staticmethod
    def check_account_locked(username, ip_address):
        """
        检查账户是否被锁定
        
        Args:
            username: 用户名
            ip_address: IP地址
            
        Returns:
            (是否被锁定, 锁定信息)
        """
        try:
            # 检查用户锁定
            user_lock = AccountLock.query.filter(
                AccountLock.username == username,
                AccountLock.lock_type.in_(['user', 'both']),
                AccountLock.is_active == True
            ).first()
            
            if user_lock and user_lock.is_valid():
                return True, {
                    'type': 'user',
                    'reason': user_lock.reason,
                    'expires_at': user_lock.expires_at.isoformat()
                }
            
            # 检查IP锁定
            ip_lock = AccountLock.query.filter(
                AccountLock.ip_address == ip_address,
                AccountLock.lock_type.in_(['ip', 'both']),
                AccountLock.is_active == True
            ).first()
            
            if ip_lock and ip_lock.is_valid():
                return True, {
                    'type': 'ip',
                    'reason': ip_lock.reason,
                    'expires_at': ip_lock.expires_at.isoformat()
                }
            
            return False, None
            
        except Exception as e:
            current_app.logger.error(f"检查账户锁定失败: {str(e)}")
            return False, None
    
    @staticmethod
    def check_login_attempts(username, ip_address):
        """
        检查登录尝试次数
        
        Args:
            username: 用户名
            ip_address: IP地址
            
        Returns:
            (是否超过限制, 剩余尝试次数)
        """
        try:
            # 检查用户登录尝试次数（最近1小时）
            user_attempts = LoginLog.query.filter(
                LoginLog.username == username,
                LoginLog.login_type == 'failed',
                LoginLog.created_at >= datetime.now(timezone.utc) - timedelta(hours=1)
            ).count()
            
            if user_attempts >= AccountSecurityService.MAX_LOGIN_ATTEMPTS:
                return True, 0
            
            # 检查IP登录尝试次数（最近1小时）
            ip_attempts = LoginLog.query.filter(
                LoginLog.ip_address == ip_address,
                LoginLog.login_type == 'failed',
                LoginLog.created_at >= datetime.now(timezone.utc) - timedelta(hours=1)
            ).count()
            
            if ip_attempts >= AccountSecurityService.IP_MAX_ATTEMPTS:
                return True, 0
            
            # 返回剩余尝试次数
            remaining_user = max(0, AccountSecurityService.MAX_LOGIN_ATTEMPTS - user_attempts)
            remaining_ip = max(0, AccountSecurityService.IP_MAX_ATTEMPTS - ip_attempts)
            remaining = min(remaining_user, remaining_ip)
            
            return False, remaining
            
        except Exception as e:
            current_app.logger.error(f"检查登录尝试次数失败: {str(e)}")
            return False, 0
    
    @staticmethod
    def lock_account(username, ip_address, reason, lock_type='both'):
        """
        锁定账户
        
        Args:
            username: 用户名
            ip_address: IP地址
            reason: 锁定原因
            lock_type: 锁定类型 ('user', 'ip', 'both')
        """
        try:
            # 计算过期时间
            if lock_type in ['user', 'both']:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=AccountSecurityService.LOCK_DURATION_HOURS)
            else:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=AccountSecurityService.IP_LOCK_DURATION_HOURS)
            
            # 创建锁定记录
            lock = AccountLock(
                username=username,
                ip_address=ip_address,
                lock_type=lock_type,
                reason=reason,
                expires_at=expires_at
            )
            
            db.session.add(lock)
            db.session.commit()
            
            current_app.logger.warning(f"账户被锁定: {username} - {reason}")
            
        except Exception as e:
            current_app.logger.error(f"锁定账户失败: {str(e)}")
            db.session.rollback()
    
    @staticmethod
    def unlock_expired_accounts():
        """解锁过期的账户"""
        try:
            expired_locks = AccountLock.query.filter(
                AccountLock.is_active == True,
                AccountLock.expires_at < datetime.now(timezone.utc)
            ).all()
            
            for lock in expired_locks:
                lock.unlock()
            
            if expired_locks:
                current_app.logger.info(f"解锁了 {len(expired_locks)} 个过期账户")
            
        except Exception as e:
            current_app.logger.error(f"解锁过期账户失败: {str(e)}")
    
    @staticmethod
    def get_login_history(user_id, limit=50):
        """
        获取用户登录历史
        
        Args:
            user_id: 用户ID
            limit: 限制数量
            
        Returns:
            登录历史列表
        """
        try:
            logs = LoginLog.query.filter_by(user_id=user_id)\
                .order_by(LoginLog.created_at.desc())\
                .limit(limit)\
                .all()
            
            return [log.to_dict() for log in logs]
            
        except Exception as e:
            current_app.logger.error(f"获取登录历史失败: {str(e)}")
            return []
    
    @staticmethod
    def get_security_stats():
        """
        获取安全统计信息
        
        Returns:
            安全统计信息
        """
        try:
            now = datetime.now(timezone.utc)
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)
            
            # 最近24小时登录统计
            recent_logins = LoginLog.query.filter(
                LoginLog.created_at >= last_24h
            ).count()
            
            recent_failed = LoginLog.query.filter(
                LoginLog.created_at >= last_24h,
                LoginLog.login_type == 'failed'
            ).count()
            
            recent_success = LoginLog.query.filter(
                LoginLog.created_at >= last_24h,
                LoginLog.login_type == 'success'
            ).count()
            
            # 最近7天登录统计
            weekly_logins = LoginLog.query.filter(
                LoginLog.created_at >= last_7d
            ).count()
            
            # 当前锁定账户数
            locked_accounts = AccountLock.query.filter(
                AccountLock.is_active == True,
                AccountLock.expires_at > now
            ).count()
            
            return {
                'recent_24h': {
                    'total_logins': recent_logins,
                    'successful_logins': recent_success,
                    'failed_logins': recent_failed,
                    'success_rate': (recent_success / recent_logins * 100) if recent_logins > 0 else 0
                },
                'weekly_logins': weekly_logins,
                'locked_accounts': locked_accounts,
                'timestamp': now.isoformat()
            }
            
        except Exception as e:
            current_app.logger.error(f"获取安全统计失败: {str(e)}")
            return {}
    
    @staticmethod
    def cleanup_old_logs(days=30):
        """清理旧的登录日志"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            old_logs = LoginLog.query.filter(
                LoginLog.created_at < cutoff_date
            ).count()
            
            LoginLog.query.filter(
                LoginLog.created_at < cutoff_date
            ).delete()
            
            db.session.commit()
            
            if old_logs > 0:
                current_app.logger.info(f"清理了 {old_logs} 条旧登录日志")
            
        except Exception as e:
            current_app.logger.error(f"清理旧日志失败: {str(e)}")
            db.session.rollback()
