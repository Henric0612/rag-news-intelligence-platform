"""
Sprint 1：基础设施层 - 认证服务单元测试
测试用例：AUTH-001, AUTH-002, AUTH-003, AUTH-004
"""
import pytest
from Backend.services.auth_service import AuthService
from Backend.models.user import User
from Backend.models import db


class TestSprint1AuthService:
    """Sprint 1：认证服务测试（4个核心用例）"""
    
    def test_register_user_success(self, app):
        """AUTH-001: 用户注册（有效数据）"""
        with app.app_context():
            user = AuthService.register_user(
                username='testuser',
                email='test@example.com',
                password='TestPass123!'
            )
            
            assert user is not None
            assert user.username == 'testuser'
            assert user.email == 'test@example.com'
            assert user.is_active is True
            # 验证密码已加密
            assert user.password_hash != 'TestPass123!'
            print("✓ 用户注册成功")
    
    def test_authenticate_user_success(self, app):
        """AUTH-002: 用户登录（正确凭据）"""
        with app.app_context():
            # 先注册用户
            AuthService.register_user(
                username='testuser',
                email='test@example.com',
                password='TestPass123!'
            )
            
            # 测试用户名登录
            user = AuthService.authenticate_user('testuser', 'TestPass123!')
            assert user is not None
            assert user.username == 'testuser'
            
            # 测试邮箱登录
            user = AuthService.authenticate_user('test@example.com', 'TestPass123!')
            assert user is not None
            assert user.email == 'test@example.com'
            print("✓ 用户登录成功")
    
    def test_jwt_token_generation(self, app):
        """AUTH-003: JWT Token生成验证"""
        with app.app_context():
            # 注册并登录用户
            user = AuthService.register_user(
                username='testuser',
                email='test@example.com',
                password='TestPass123!'
            )
            
            # 生成Token
            from Backend.utils.jwt_utils import create_access_token, create_refresh_token
            access_token = create_access_token(user.id)
            refresh_token = create_refresh_token(user.id)
            
            assert access_token is not None
            assert refresh_token is not None
            assert isinstance(access_token, str)
            assert isinstance(refresh_token, str)
            print("✓ JWT Token生成成功")
    
    def test_password_encryption(self, app):
        """AUTH-004: 密码加密验证"""
        with app.app_context():
            password = 'TestPass123!'
            user = AuthService.register_user(
                username='testuser',
                email='test@example.com',
                password=password
            )
            
            # 验证密码已加密（不是明文）
            assert user.password_hash != password
            # 验证密码哈希长度合理（bcrypt通常60字符）
            assert len(user.password_hash) > 50
            # 验证可以正确验证密码
            assert user.check_password(password) is True
            assert user.check_password('wrongpassword') is False
            print("✓ 密码加密验证成功")
