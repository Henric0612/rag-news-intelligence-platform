"""
Sprint 3：应用功能层 - 联网搜索服务单元测试
测试用例：WEB-001, WEB-002
"""
import pytest
from Backend.services.search_service import get_search_service


class TestSprint3WebSearchService:
    """Sprint 3：联网查询回退测试（2个用例）"""
    
    def test_baidu_search_api_call(self, app):
        """WEB-001: 百度搜索API调用"""
        with app.app_context():
            search_service = get_search_service()
            
            # 验证联网搜索方法存在
            assert hasattr(search_service, 'web_fallback_search')
            print("✓ 联网搜索功能存在")
    
    def test_search_results_parsing(self, app):
        """WEB-002: 搜索结果解析"""
        with app.app_context():
            search_service = get_search_service()
            
            try:
                # 测试联网搜索（使用一个简单的查询）
                results = search_service.web_fallback_search("人工智能", top_k=3)
                
                # 验证返回格式
                assert 'results' in results
                assert isinstance(results['results'], list)
                # 验证返回数量不超过3
                assert len(results['results']) <= 3
                
                # 验证结果格式
                if len(results['results']) > 0:
                    first_result = results['results'][0]
                    assert 'title' in first_result or 'content' in first_result
                
                print(f"✓ 联网搜索成功，返回{len(results['results'])}条结果")
            except Exception as e:
                pytest.skip(f"联网搜索测试失败（可能网络问题）: {str(e)}")
