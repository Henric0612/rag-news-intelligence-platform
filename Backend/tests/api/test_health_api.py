"""
Sprint 1：基础设施层 - 健康检查API测试
测试用例：HEALTH-API-001, HEALTH-API-002
"""
import pytest


class TestSprint1HealthAPI:
    """Sprint 1：健康检查API测试（2个用例）"""
    
    def test_health_check(self, client):
        """HEALTH-API-001: GET /api/health"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'status' in result['data']
        assert result['data']['status'] == 'healthy'
        
        # 验证包含必要的健康信息
        assert 'timestamp' in result['data']
        assert 'version' in result['data'] or 'uptime' in result['data']
        print("✓ 健康检查API测试通过")
    
    def test_readiness_check(self, client):
        """HEALTH-API-002: GET /api/ready"""
        response = client.get('/api/ready')
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'status' in result['data']
        
        # 验证数据库连接状态
        assert 'database' in result['data']
        assert result['data']['database'] in ['connected', 'ready', True]
        print("✓ 就绪检查API测试通过")
    
    def test_health_check_includes_system_info(self, client):
        """测试健康检查包含系统信息"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        result = response.get_json()
        
        # 可能包含的系统信息
        data = result['data']
        # 至少应该有状态和时间戳
        assert 'status' in data
        assert 'timestamp' in data
        print("✓ 健康检查包含系统信息测试通过")
    
    def test_health_endpoints_no_auth_required(self, client):
        """测试健康检查端点无需认证"""
        # 健康检查不需要认证
        health_response = client.get('/api/health')
        assert health_response.status_code == 200
        
        # 就绪检查也不需要认证
        ready_response = client.get('/api/ready')
        assert ready_response.status_code == 200
        print("✓ 健康检查端点无需认证测试通过")
