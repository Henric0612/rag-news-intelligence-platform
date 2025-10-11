"""
Sprint 2：数据与AI服务层 - 搜索API测试
测试用例：SEARCH-API-001, SEARCH-API-002
"""
import pytest


class TestSprint2SearchAPI:
    """Sprint 2：搜索API测试（2个用例）"""
    
    def test_semantic_search_api(self, client, auth_headers):
        """SEARCH-API-001: POST /api/search"""
        data = {
            'query': '人工智能发展',
            'top_k': 5
        }
        
        response = client.post('/api/search/query', 
                             json=data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        # 搜索API直接返回搜索结果，不是标准的success/data格式
        assert 'results' in result
        assert 'total' in result
        assert 'response_time' in result
        print(f"[PASS] 语义搜索API测试通过，返回{result['total']}条结果")
    
    def test_search_suggestions_api(self, client, auth_headers):
        """SEARCH-API-002: GET /api/search/suggestions"""
        response = client.get('/api/search/suggestions?q=人工', 
                            headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'data' in result
        assert isinstance(result['data'], list)
        print(f"[PASS] 搜索建议API测试通过，返回{len(result['data'])}条建议")
    
    def test_search_with_empty_query(self, client, auth_headers):
        """测试空查询处理"""
        data = {
            'query': '',
            'top_k': 5
        }
        
        response = client.post('/api/search/query', 
                             json=data, 
                             headers=auth_headers)
        
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        print("[PASS] 空查询正确拒绝")
    
    def test_search_with_invalid_auth(self, client):
        """测试无效认证"""
        data = {
            'query': '人工智能发展',
            'top_k': 5
        }
        
        response = client.post('/api/search/query', json=data)
        
        assert response.status_code == 401
        result = response.get_json()
        assert 'msg' in result or 'message' in result
        print("[PASS] 无效认证正确拒绝")
    
    def test_search_with_filters(self, client, auth_headers):
        """测试带过滤条件的搜索"""
        data = {
            'query': '人工智能',
            'top_k': 5,
            'filters': {
                'category': '科技'
            }
        }
        
        response = client.post('/api/search/query', 
                             json=data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert 'results' in result
        print("[PASS] 带过滤条件的搜索测试通过")
    
    def test_search_pagination(self, client, auth_headers):
        """测试搜索结果限制（使用 top_k）"""
        data = {
            'query': '测试',
            'top_k': 10
        }
        
        response = client.post('/api/search/query', 
                             json=data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert 'results' in result
        assert 'total' in result
        # 验证返回结果数量不超过 top_k
        if result.get('results'):
            assert len(result['results']) <= 10
        print("[PASS] 搜索结果限制测试通过")
    
    def test_search_health_check(self, client):
        """测试搜索服务健康检查"""
        response = client.get('/api/search/health')
        
        if response.status_code == 200:
            result = response.get_json()
            assert result['success'] is True
            assert 'data' in result
            print("[PASS] 搜索服务健康检查测试通过")
        elif response.status_code == 404:
            print("⚠ 搜索健康检查端点不存在（可选功能）")
        else:
            pytest.fail(f"意外的状态码: {response.status_code}")