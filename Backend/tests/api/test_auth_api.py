"""
Sprint 1：基础设施层 - 认证API测试
测试用例：AUTH-API-001, AUTH-API-002, AUTH-API-003
"""
import pytest


class TestSprint1AuthAPI:
    """Sprint 1：认证API测试（3个用例）"""
    
    def test_register_success(self, client):
        """AUTH-API-001: POST /api/auth/register"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        
        response = client.post('/api/auth/register', json=data)
        
        assert response.status_code == 201
        result = response.get_json()
        assert result['success'] is True
        assert 'data' in result
        assert 'user' in result['data']
        assert result['data']['user']['username'] == 'testuser'
        assert result['data']['user']['email'] == 'test@example.com'
        print("✓ 用户注册API测试通过")
    
    def test_register_duplicate_email(self, client):
        """测试重复邮箱注册"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        
        # 第一次注册
        response1 = client.post('/api/auth/register', json=data)
        assert response1.status_code == 201
        
        # 第二次注册相同邮箱
        data['username'] = 'testuser2'
        response2 = client.post('/api/auth/register', json=data)
        
        assert response2.status_code == 400
        result = response2.get_json()
        assert result['success'] is False
        assert '邮箱已被注册' in result['message']
        print("✓ 重复邮箱注册正确拒绝")
    
    def test_register_invalid_email(self, client):
        """测试无效邮箱格式"""
        data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'TestPass123!'
        }
        
        response = client.post('/api/auth/register', json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        print("✓ 无效邮箱格式正确拒绝")
    
    def test_register_weak_password(self, client):
        """测试弱密码"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123'  # 弱密码
        }
        
        response = client.post('/api/auth/register', json=data)
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        print("✓ 弱密码正确拒绝")
    
    def test_login_success(self, client):
        """AUTH-API-002: POST /api/auth/login"""
        # 先注册用户
        register_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        client.post('/api/auth/register', json=register_data)
        
        # 测试用户名登录
        login_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        response = client.post('/api/auth/login', json=login_data)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'tokens' in result['data']
        assert 'access_token' in result['data']['tokens']
        assert 'user' in result['data']
        print("✓ 用户登录API测试通过")
    
    def test_login_with_email(self, client):
        """测试使用邮箱登录"""
        # 先注册用户
        register_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        client.post('/api/auth/register', json=register_data)
        
        # 测试邮箱登录
        login_data = {
            'username': 'test@example.com',
            'password': 'TestPass123!'
        }
        response = client.post('/api/auth/login', json=login_data)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'tokens' in result['data']
        print("✓ 邮箱登录测试通过")
    
    def test_login_wrong_password(self, client):
        """测试错误密码登录"""
        # 先注册用户
        register_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        client.post('/api/auth/register', json=register_data)
        
        # 测试错误密码
        login_data = {
            'username': 'testuser',
            'password': 'WrongPassword123!'
        }
        response = client.post('/api/auth/login', json=login_data)
        
        assert response.status_code == 401
        result = response.get_json()
        assert result['success'] is False
        print("✓ 错误密码正确拒绝")
    
    def test_login_nonexistent_user(self, client):
        """测试不存在的用户登录"""
        login_data = {
            'username': 'nonexistent',
            'password': 'TestPass123!'
        }
        response = client.post('/api/auth/login', json=login_data)
        
        assert response.status_code == 401
        result = response.get_json()
        assert result['success'] is False
        print("✓ 不存在用户正确拒绝")
    
    def test_refresh_token(self, client):
        """AUTH-API-003: POST /api/auth/refresh"""
        # 先注册并登录
        register_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        client.post('/api/auth/register', json=register_data)
        
        login_response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'TestPass123!'
        })
        refresh_token = login_response.get_json()['data']['tokens']['refresh_token']
        
        # 刷新token
        response = client.post('/api/auth/refresh', 
                             headers={'Authorization': f'Bearer {refresh_token}'})
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'tokens' in result['data']
        assert 'access_token' in result['data']['tokens']
        print("✓ Token刷新API测试通过")
    
    def test_refresh_token_invalid(self, client):
        """测试无效refresh token"""
        response = client.post('/api/auth/refresh',
                             headers={'Authorization': 'Bearer invalid_token'})
        
        assert response.status_code == 401
        result = response.get_json()
        assert result['success'] is False
        print("✓ 无效refresh token正确拒绝")
    
    def test_get_user_info(self, client, auth_headers):
        """测试获取用户信息"""
        response = client.get('/api/auth/me', headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'user' in result['data']
        assert 'username' in result['data']['user']
        assert 'email' in result['data']['user']
        print("✓ 获取用户信息测试通过")
    
    def test_get_user_info_unauthorized(self, client):
        """测试未授权获取用户信息"""
        response = client.get('/api/auth/me')
        
        assert response.status_code == 401
        result = response.get_json()
        assert result['success'] is False
        print("✓ 未授权访问正确拒绝")