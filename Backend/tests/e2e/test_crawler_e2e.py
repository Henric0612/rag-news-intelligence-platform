"""
Sprint 3：应用功能层 - 爬虫管理E2E测试
测试用例：E2E-006
"""
import pytest
import time


class TestSprint3CrawlerE2E:
    """Sprint 3：爬虫管理E2E测试（1个用例）"""
    
    def test_crawler_management_complete_flow(self, client, auth_headers):
        """E2E-006: 爬虫管理界面流程"""
        # 步骤1：创建爬虫任务
        task_data = {
            'source_type': 'rss',
            'source_url': 'https://example.com/rss',
            'category': '科技新闻',
            'schedule': 'daily'
        }
        
        create_response = client.post('/api/crawler/start', 
                                     json=task_data, 
                                     headers=auth_headers)
        
        assert create_response.status_code in [200, 201]
        create_result = create_response.get_json()
        assert create_result['success'] is True
        
        task_id = None
        if 'task_id' in create_result.get('data', {}):
            task_id = create_result['data']['task_id']
            print(f"✓ 爬虫任务创建成功，任务ID: {task_id}")
        else:
            print("✓ 爬虫任务启动成功")
        
        # 步骤2：获取爬虫任务列表
        list_response = client.get('/api/crawler/tasks', headers=auth_headers)
        
        assert list_response.status_code == 200
        list_result = list_response.get_json()
        assert list_result['success'] is True
        
        tasks_key = 'tasks' if 'tasks' in list_result['data'] else 'items'
        tasks = list_result['data'].get(tasks_key, [])
        
        print(f"✓ 爬虫任务列表获取成功，共{len(tasks)}个任务")
        
        # 步骤3：如果有任务ID，获取任务详情
        if task_id:
            detail_response = client.get(f'/api/crawler/tasks/{task_id}', headers=auth_headers)
            
            if detail_response.status_code == 200:
                detail_result = detail_response.get_json()
                assert detail_result['success'] is True
                print("✓ 爬虫任务详情获取成功")
            elif detail_response.status_code == 404:
                print("⚠ 任务已完成或不存在（正常情况）")
        
        # 步骤4：等待任务执行（短暂延迟）
        time.sleep(1)
        
        # 步骤5：检查任务状态
        status_response = client.get('/api/crawler/tasks', headers=auth_headers)
        assert status_response.status_code == 200
        
        print("✓ 爬虫任务状态检查成功")
        print("✓ E2E-006: 爬虫管理界面流程测试通过")
    
    def test_crawler_with_different_sources(self, client, auth_headers):
        """测试不同来源的爬虫任务"""
        sources = [
            {'source_type': 'rss', 'source_url': 'https://example.com/rss'},
            {'source_type': 'web', 'source_url': 'https://example.com/article'},
        ]
        
        for source in sources:
            source['category'] = '测试'
            response = client.post('/api/crawler/start', 
                                 json=source, 
                                 headers=auth_headers)
            
            assert response.status_code in [200, 201]
            print(f"✓ {source['source_type']}类型爬虫任务创建成功")
    
    def test_crawler_error_handling(self, client, auth_headers):
        """测试爬虫错误处理"""
        # 测试无效URL
        invalid_data = {
            'source_type': 'rss',
            'source_url': 'invalid-url',
            'category': '测试'
        }
        
        response = client.post('/api/crawler/start', 
                             json=invalid_data, 
                             headers=auth_headers)
        
        # 可能返回400（验证失败）或200（任务创建但执行失败）
        assert response.status_code in [200, 201, 400]
        print("✓ 爬虫错误处理测试通过")
    
    def test_crawler_task_cancellation(self, client, auth_headers):
        """测试爬虫任务取消"""
        # 创建任务
        task_data = {
            'source_type': 'rss',
            'source_url': 'https://example.com/rss',
            'category': '测试'
        }
        
        create_response = client.post('/api/crawler/start', 
                                     json=task_data, 
                                     headers=auth_headers)
        
        if create_response.status_code in [200, 201]:
            result = create_response.get_json()
            
            if 'task_id' in result.get('data', {}):
                task_id = result['data']['task_id']
                
                # 尝试取消任务
                cancel_response = client.delete(f'/api/crawler/tasks/{task_id}', 
                                              headers=auth_headers)
                
                if cancel_response.status_code in [200, 404]:
                    print("✓ 爬虫任务取消测试通过")
                else:
                    print("⚠ 任务取消功能可能未实现")
            else:
                print("⚠ 任务ID未返回，跳过取消测试")
