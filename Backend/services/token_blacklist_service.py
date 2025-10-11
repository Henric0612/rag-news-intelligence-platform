"""
Token黑名单服务
用于管理已登出或失效的JWT Token
使用内存存储，避免Redis依赖
"""
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TokenBlacklistService:
    """Token黑名单服务（内存实现）"""
    
    # 使用类变量存储黑名单（所有实例共享）
    _blacklist: Dict[str, datetime] = {}
    _lock = Lock()
    
    @classmethod
    def add_to_blacklist(cls, token: str, expires_at: Optional[datetime] = None) -> bool:
        """
        将token加入黑名单
        
        Args:
            token: JWT token字符串
            expires_at: token的过期时间（用于自动清理）
            
        Returns:
            bool: 是否成功添加
        """
        try:
            with cls._lock:
                cls._blacklist[token] = expires_at or datetime.now(timezone.utc)
                logger.info(f"Token已加入黑名单，当前黑名单大小: {len(cls._blacklist)}")
                
                # 清理已过期的token（防止内存泄漏）
                cls._cleanup_expired_tokens()
                
                return True
        except Exception as e:
            logger.error(f"添加token到黑名单失败: {str(e)}")
            return False
    
    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        """
        检查token是否在黑名单中
        
        Args:
            token: JWT token字符串
            
        Returns:
            bool: 是否在黑名单中
        """
        try:
            with cls._lock:
                if token in cls._blacklist:
                    # 检查是否已过期
                    expires_at = cls._blacklist[token]
                    if expires_at and datetime.now(timezone.utc) > expires_at:
                        # 已过期，从黑名单移除
                        del cls._blacklist[token]
                        return False
                    return True
                return False
        except Exception as e:
            logger.error(f"检查token黑名单失败: {str(e)}")
            return False
    
    @classmethod
    def remove_from_blacklist(cls, token: str) -> bool:
        """
        从黑名单中移除token
        
        Args:
            token: JWT token字符串
            
        Returns:
            bool: 是否成功移除
        """
        try:
            with cls._lock:
                if token in cls._blacklist:
                    del cls._blacklist[token]
                    logger.info(f"Token已从黑名单移除")
                    return True
                return False
        except Exception as e:
            logger.error(f"从黑名单移除token失败: {str(e)}")
            return False
    
    @classmethod
    def _cleanup_expired_tokens(cls) -> int:
        """
        清理已过期的token（内部方法）
        
        Returns:
            int: 清理的token数量
        """
        try:
            now = datetime.now(timezone.utc)
            expired_tokens = [
                token for token, expires_at in cls._blacklist.items()
                if expires_at and now > expires_at
            ]
            
            for token in expired_tokens:
                del cls._blacklist[token]
            
            if expired_tokens:
                logger.info(f"清理了 {len(expired_tokens)} 个过期token")
            
            return len(expired_tokens)
        except Exception as e:
            logger.error(f"清理过期token失败: {str(e)}")
            return 0
    
    @classmethod
    def get_blacklist_size(cls) -> int:
        """
        获取黑名单大小
        
        Returns:
            int: 黑名单中的token数量
        """
        with cls._lock:
            return len(cls._blacklist)
    
    @classmethod
    def clear_all(cls) -> bool:
        """
        清空黑名单（谨慎使用）
        
        Returns:
            bool: 是否成功清空
        """
        try:
            with cls._lock:
                cls._blacklist.clear()
                logger.warning("黑名单已清空")
                return True
        except Exception as e:
            logger.error(f"清空黑名单失败: {str(e)}")
            return False

