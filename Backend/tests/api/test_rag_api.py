"""
Sprint 2：数据与AI服务层 - RAG API测试
测试用例：RAG-API-001, RAG-API-002
"""
import pytest


class TestSprint2RAGAPI:
    """Sprint 2：RAG API测试（2个用例）"""
    
    def test_rag_question_answering_api(self, client, auth_headers):
        """RAG-API-001: POST /api/rag/ask"""
        data = {
            'query': '什么是人工智能？',
            'stream': False
        }
        
        response = client.post('/api/rag/ask', 
                             json=data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'data' in result
        assert 'answer' in result['data']
        assert 'sources' in result['data']
        assert 'response_time' in result['data']
        assert 'query' in result['data']
        print("✓ RAG问答API测试通过")
    
    def test_rag_context_api(self, client, auth_headers):
        """RAG-API-002: GET /api/rag/context"""
        data = {
            'documents': [
                {'content': '人工智能是计算机科学的一个分支', 'title': 'AI定义'},
                {'content': '机器学习是AI的重要组成部分', 'title': '机器学习'}
            ],
            'max_length': 1000
        }
        
        response = client.post('/api/rag/context', 
                             json=data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'data' in result
        assert 'context' in result['data']
        print("✓ 上下文获取API测试通过")
    
    def test_rag_with_empty_query(self, client, auth_headers):
        """测试空查询处理"""
        data = {
            'query': '',
            'stream': False
        }
        
        response = client.post('/api/rag/ask', 
                             json=data, 
                             headers=auth_headers)
        
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        print("✓ 空查询正确拒绝")
    
    def test_rag_with_invalid_auth(self, client):
        """测试无效认证"""
        data = {
            'query': '什么是人工智能？',
            'stream': False
        }
        
        response = client.post('/api/rag/ask', json=data)
        
        assert response.status_code == 401
        result = response.get_json()
        assert 'msg' in result or 'message' in result
        print("✓ 无效认证正确拒绝")
    
    def test_rag_with_web_fallback(self, client, auth_headers):
        """测试RAG联网回退功能"""
        data = {
            'query': '2025年最新的量子计算进展',
            'stream': False,
            'enable_web_fallback': True
        }
        
        response = client.post('/api/rag/ask', 
                             json=data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'data' in result
        print("✓ RAG联网回退功能测试通过")
    
    def test_rag_vector_search_api(self, client, auth_headers):
        """测试向量搜索API"""
        data = {
            'query': '机器学习算法',
            'top_k': 3
        }
        
        response = client.post('/api/rag/vector-search', 
                             json=data, 
                             headers=auth_headers)
        
        if response.status_code == 200:
            result = response.get_json()
            assert result['success'] is True
            assert 'data' in result
            assert isinstance(result['data'], list)
            print("✓ 向量搜索API测试通过")
        elif response.status_code == 404:
            print("⚠ 向量搜索端点不存在（可选功能）")
        else:
            pytest.fail(f"意外的状态码: {response.status_code}")
    
    def test_rag_generate_api(self, client, auth_headers):
        """测试直接LLM生成API"""
        data = {
            'query': '请解释什么是深度学习',
            'context': [],
            'options': {}
        }
        
        response = client.post('/api/rag/generate', 
                             json=data, 
                             headers=auth_headers)
        
        if response.status_code == 200:
            result = response.get_json()
            assert result['success'] is True
            assert 'data' in result
            assert 'answer' in result['data']
            print("✓ 直接LLM生成API测试通过")
        elif response.status_code == 404:
            print("⚠ LLM生成端点不存在（可选功能）")
        else:
            pytest.fail(f"意外的状态码: {response.status_code}")