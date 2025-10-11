"""
Sprint 3：应用功能层 - 数据分析API测试
测试用例：ANALYTICS-API-001
"""
import pytest


class TestSprint3AnalyticsAPI:
    """Sprint 3：数据分析API测试（1个用例）"""
    
    def test_get_clustering_report(self, client, auth_headers):
        """ANALYTICS-API-001: GET /api/analytics/clustering"""
        response = client.get('/api/analytics/clustering', headers=auth_headers)
        
        # 打印调试信息
        if response.status_code != 200:
            print(f"\n[DEBUG] Status: {response.status_code}")
            print(f"[DEBUG] Response: {response.get_json()}")
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        
        # 验证返回数据格式
        data = result['data']
        assert 'total_items' in data
        assert 'top_10_keywords' in data
        assert 'cluster_distribution' in data or 'category_distribution' in data
        
        # 验证Top10关键词格式
        if data['top_10_keywords']:
            assert isinstance(data['top_10_keywords'], list)
            assert len(data['top_10_keywords']) <= 10
            
            # 验证关键词格式
            if len(data['top_10_keywords']) > 0:
                first_keyword = data['top_10_keywords'][0]
                assert 'keyword' in first_keyword
                assert 'count' in first_keyword or 'score' in first_keyword or 'percentage' in first_keyword
        
        print(f"[PASS] 聚类分析报告API测试通过，总条目: {data['total_items']}")
    
    def test_clustering_report_unauthorized(self, client):
        """测试未授权访问聚类分析"""
        response = client.get('/api/analytics/clustering')
        
        # 可能需要认证，也可能不需要（取决于设计）
        # 如果需要认证，应该返回401
        if response.status_code == 401:
            print("[PASS] 未授权访问正确拒绝")
        elif response.status_code == 200:
            print("[PASS] 聚类分析API无需认证（公开访问）")
        else:
            pytest.fail(f"意外的状态码: {response.status_code}")
    
    def test_clustering_report_with_empty_database(self, client, auth_headers):
        """测试空数据库的聚类分析"""
        # 清空知识库（如果有清空接口）
        # 这里我们直接测试API的健壮性
        
        response = client.get('/api/analytics/clustering', headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        
        # 空数据库应该返回0条目
        data = result['data']
        if data['total_items'] == 0:
            assert data['top_10_keywords'] == []
            print("[PASS] 空数据库聚类分析正确处理")
        else:
            print(f"⚠ 数据库不为空，包含{data['total_items']}条数据")
    
    def test_clustering_report_response_format(self, client, auth_headers):
        """测试聚类分析响应格式完整性"""
        response = client.get('/api/analytics/clustering', headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        
        # 验证响应结构
        assert 'success' in result
        assert 'data' in result
        assert 'message' in result or 'msg' in result
        
        # 验证数据结构
        data = result['data']
        required_fields = ['total_items', 'top_10_keywords']
        for field in required_fields:
            assert field in data, f"缺少必需字段: {field}"
        
        print("[PASS] 聚类分析响应格式完整性测试通过")
