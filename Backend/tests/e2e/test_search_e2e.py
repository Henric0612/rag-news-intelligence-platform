"""
Sprint 2：数据与AI服务层 - 智能搜索E2E测试
测试用例：E2E-001
"""
import pytest
import time


class TestSprint2SearchE2E:
    """Sprint 2：智能搜索E2E测试（1个用例）"""
    
    def test_semantic_search_complete_flow(self, client, auth_headers):
        """E2E-001: 智能搜索完整流程"""
        # 步骤1：执行语义搜索
        search_data = {
            'query': '人工智能在医疗领域的应用',
            'top_k': 5
        }
        
        start_time = time.time()
        search_response = client.post('/api/search/query', 
                                    json=search_data, 
                                    headers=auth_headers)
        search_time = time.time() - start_time
        
        assert search_response.status_code == 200
        search_result = search_response.get_json()
        
        # 验证搜索结果结构
        assert 'results' in search_result
        assert 'total' in search_result
        assert 'response_time' in search_result
        
        print(f"[PASS] 语义搜索执行成功，返回{search_result['total']}条结果")
        
        # 步骤2：获取搜索建议
        suggestions_response = client.get('/api/search/suggestions?q=人工智能', 
                                        headers=auth_headers)
        
        assert suggestions_response.status_code == 200
        suggestions_result = suggestions_response.get_json()
        assert suggestions_result['success'] is True
        assert isinstance(suggestions_result['data'], list)
        
        print(f"[PASS] 搜索建议获取成功，返回{len(suggestions_result['data'])}条建议")
        
        # 步骤3：验证搜索性能
        response_time = search_result.get('response_time', search_time)
        assert response_time < 2.0, f"搜索响应时间过长: {response_time}秒"
        
        print(f"[PASS] 搜索性能达标，响应时间: {response_time:.3f}秒")
        
        # 步骤4：验证搜索结果质量
        if search_result['total'] > 0:
            first_result = search_result['results'][0]
            assert 'title' in first_result or 'content' in first_result
            assert 'score' in first_result or 'similarity_score' in first_result
            print("[PASS] 搜索结果格式正确")
        else:
            print("⚠ 知识库为空，无搜索结果")
        
        print("[PASS] E2E-001: 智能搜索完整流程测试通过")
    
    def test_search_with_filters(self, client, auth_headers):
        """测试带过滤条件的搜索流程"""
        # 步骤1：按分类搜索（使用 filters 对象）
        search_data = {
            'query': '人工智能',
            'top_k': 5,
            'filters': {
                'category': '科技'
            }
        }
        
        response = client.post('/api/search/query', 
                             json=search_data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert 'results' in result
        print("[PASS] 分类过滤搜索测试通过")
    
    def test_search_pagination_flow(self, client, auth_headers):
        """测试搜索结果限制流程（使用 top_k）"""
        # 步骤1：获取前10条结果
        search_data = {
            'query': '测试',
            'top_k': 10
        }
        
        response1 = client.post('/api/search/query', 
                              json=search_data, 
                              headers=auth_headers)
        
        assert response1.status_code == 200
        result1 = response1.get_json()
        assert 'results' in result1
        
        # 验证结果数量不超过 top_k
        if result1.get('results'):
            assert len(result1['results']) <= 10, "结果数量超过 top_k 限制"
        
        # 步骤2：获取前5条结果
        search_data['top_k'] = 5
        response2 = client.post('/api/search/query', 
                              json=search_data, 
                              headers=auth_headers)
        
        assert response2.status_code == 200
        result2 = response2.get_json()
        
        # 验证结果数量不超过新的 top_k
        if result2.get('results'):
            assert len(result2['results']) <= 5, "结果数量超过 top_k 限制"
        
        print(f"[PASS] 搜索结果限制测试通过，top_k=10时{len(result1.get('results', []))}条，top_k=5时{len(result2.get('results', []))}条")
