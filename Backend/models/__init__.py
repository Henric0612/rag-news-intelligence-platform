"""
数据模型包
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User
from .knowledge import KnowledgeItem
from .search_history import SearchHistory
from .rss_source import RSSSource
from .crawl_task import CrawlTask
from .password_reset import PasswordResetToken
from .login_log import LoginLog, AccountLock
from .email_verification import EmailVerificationToken

__all__ = ['db', 'User', 'KnowledgeItem', 'SearchHistory', 'RSSSource', 'CrawlTask', 'PasswordResetToken', 'LoginLog', 'AccountLock', 'EmailVerificationToken']
