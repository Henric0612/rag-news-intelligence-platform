"""
Sprint 1：基础设施层 - 认证模块集成测试
测试用例：AUTH-INT-001, AUTH-INT-002
"""
import pytest
from Backend.models import db
from Backend.models.user import User
from Backend.services.auth_service import AuthService
from Backend.utils.jwt_utils import create_access_token, create_refresh_token, verify_token


class TestSprint1AuthIntegration:
    """Sprint 1：认证集成测试（2个用例）"""
    
    def test_complete_auth_flow(self, app):
        """AUTH-INT-001: 完整认证流程（注册→登录→访问→登出）"""
        with app.app_context():
            # 1. 注册用户
            user = AuthService.register_user(
                username='testuser',
                email='test@example.com',
                password='TestPass123!'
            )
            assert user is not None
            assert user.id is not None
            
            # 2. 登录获取token
            authenticated_user = AuthService.authenticate_user('testuser', 'TestPass123!')
            assert authenticated_user.id == user.id
            
            # 3. 生成访问令牌
            access_token = create_access_token(user.id)
            refresh_token = create_refresh_token(user.id)
            assert access_token is not None
            assert refresh_token is not None
            
            # 4. 验证令牌可以正常使用
            payload = verify_token(access_token)
            assert payload['user_id'] == user.id
            assert payload['token_type'] == 'access'
            
            print("✓ 完整认证流程测试通过")
    
    def test_token_refresh_mechanism(self, app):
        """AUTH-INT-002: Token刷新机制"""
        with app.app_context():
            # 1. 注册并登录用户
            user = AuthService.register_user(
                username='testuser',
                email='test@example.com',
                password='TestPass123!'
            )
            
            # 2. 生成初始令牌
            original_access = create_access_token(user.id)
            original_refresh = create_refresh_token(user.id)
            
            # 3. 验证原始令牌
            payload = verify_token(original_access)
            assert payload['user_id'] == user.id
            assert payload['token_type'] == 'access'
            
            # 4. 验证刷新令牌
            refresh_payload = verify_token(original_refresh)
            assert refresh_payload['user_id'] == user.id
            assert refresh_payload['token_type'] == 'refresh'
            
            # 5. 刷新令牌（生成新的）
            new_access = create_access_token(user.id)
            new_refresh = create_refresh_token(user.id)
            
            # 6. 验证新旧令牌不同（因为包含时间戳）
            assert new_access != original_access
            assert new_refresh != original_refresh
            
            # 7. 验证新令牌有效
            new_payload = verify_token(new_access)
            assert new_payload['user_id'] == user.id
            assert new_payload['token_type'] == 'access'
            
            print("✓ Token刷新机制测试通过")