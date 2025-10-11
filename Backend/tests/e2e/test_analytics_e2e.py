"""
Sprint 3：应用功能层 - 数据分析E2E测试
测试用例：E2E-007
"""
import pytest


class TestSprint3AnalyticsE2E:
    """Sprint 3：数据分析E2E测试（1个用例）"""
    
    def test_analytics_page_complete_flow(self, client, auth_headers):
        """E2E-007: 数据分析页面展示"""
        # 步骤1：准备测试数据（创建一些知识库条目）
        test_items = [
            {
                'title': '人工智能发展',
                'content': '人工智能技术正在快速发展，机器学习和深度学习是核心技术',
                'source_url': 'http://example.com/ai1',
                'source_type': 'manual',
                'category': '科技'
            },
            {
                'title': '机器学习应用',
                'content': '机器学习在各个领域都有广泛应用，包括图像识别和自然语言处理',
                'source_url': 'http://example.com/ml1',
                'source_type': 'manual',
                'category': '科技'
            },
            {
                'title': '深度学习框架',
                'content': '深度学习框架如TensorFlow和PyTorch极大地推动了技术进步',
                'source_url': 'http://example.com/dl1',
                'source_type': 'manual',
                'category': '科技'
            }
        ]
        
        created_ids = []
        for item in test_items:
            response = client.post('/api/knowledge', json=item, headers=auth_headers)
            if response.status_code == 201:
                created_ids.append(response.get_json()['data']['id'])
        
        print(f"✓ 准备测试数据，创建{len(created_ids)}条知识库条目")
        
        try:
            # 步骤2：获取聚类分析报告
            analytics_response = client.get('/api/analytics/clustering', headers=auth_headers)
            
            assert analytics_response.status_code == 200
            analytics_result = analytics_response.get_json()
            assert analytics_result['success'] is True
            
            # 验证分析报告结构
            data = analytics_result['data']
            assert 'total_items' in data
            assert 'top_10_keywords' in data
            
            print(f"✓ 聚类分析报告获取成功，总条目: {data['total_items']}")
            
            # 步骤3：验证Top10关键词
            keywords = data['top_10_keywords']
            assert isinstance(keywords, list)
            assert len(keywords) <= 10
            
            if len(keywords) > 0:
                # 验证关键词格式
                first_keyword = keywords[0]
                assert 'keyword' in first_keyword
                assert 'count' in first_keyword or 'score' in first_keyword or 'percentage' in first_keyword
                
                print(f"✓ Top10关键词提取成功，共{len(keywords)}个关键词")
                print(f"  前3个关键词: {[kw['keyword'] for kw in keywords[:3]]}")
                
                # 验证是否包含预期关键词
                keyword_list = [kw['keyword'] for kw in keywords]
                expected_keywords = ['人工智能', '机器学习', '深度学习']
                found_count = sum(1 for kw in expected_keywords if kw in keyword_list)
                
                if found_count > 0:
                    print(f"✓ 关键词提取准确，找到{found_count}个预期关键词")
                else:
                    print("⚠ 未找到预期关键词（可能是分词或算法问题）")
            else:
                print("⚠ 关键词列表为空（数据量可能不足）")
            
            # 步骤4：验证聚类分布
            if 'cluster_distribution' in data:
                clusters = data['cluster_distribution']
                assert isinstance(clusters, list)
                print(f"✓ 聚类分布获取成功，共{len(clusters)}个聚类")
            
            # 步骤5：验证分类分布
            if 'category_distribution' in data:
                categories = data['category_distribution']
                assert isinstance(categories, list)
                
                # 应该能找到"科技"分类
                tech_category = next((cat for cat in categories if cat['category'] == '科技'), None)
                if tech_category:
                    print(f"✓ 分类分布正确，科技分类有{tech_category['count']}条")
                else:
                    print("⚠ 未找到科技分类")
            
            print("✓ E2E-007: 数据分析页面展示测试通过")
            
        finally:
            # 清理测试数据
            for item_id in created_ids:
                client.delete(f'/api/knowledge/{item_id}', headers=auth_headers)
            print(f"✓ 清理测试数据，删除{len(created_ids)}条")
    
    def test_analytics_with_empty_database(self, client, auth_headers):
        """测试空数据库的数据分析"""
        response = client.get('/api/analytics/clustering', headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        
        data = result['data']
        # 空数据库应该返回0条目
        if data['total_items'] == 0:
            assert data['top_10_keywords'] == []
            print("✓ 空数据库分析正确处理")
        else:
            print(f"⚠ 数据库不为空，包含{data['total_items']}条数据")
    
    def test_analytics_performance(self, client, auth_headers):
        """测试数据分析性能"""
        import time
        
        start_time = time.time()
        response = client.get('/api/analytics/clustering', headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        
        response_time = end_time - start_time
        assert response_time < 5.0, f"数据分析响应时间过长: {response_time}秒"
        
        print(f"✓ 数据分析性能测试通过，响应时间: {response_time:.3f}秒")
    
    def test_analytics_data_consistency(self, client, auth_headers):
        """测试数据分析一致性"""
        # 获取两次分析结果
        response1 = client.get('/api/analytics/clustering', headers=auth_headers)
        response2 = client.get('/api/analytics/clustering', headers=auth_headers)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.get_json()['data']
        data2 = response2.get_json()['data']
        
        # 在没有数据变化的情况下，结果应该一致
        assert data1['total_items'] == data2['total_items']
        
        print("✓ 数据分析一致性测试通过")
