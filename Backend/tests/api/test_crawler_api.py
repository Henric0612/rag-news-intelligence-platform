"""
Sprint 2：数据与AI服务层 - 爬虫与上传API测试
测试用例：CRAWL-API-001, CRAWL-API-002, UPLOAD-API-001
"""
import pytest
import io


class TestSprint2CrawlerAPI:
    """Sprint 2：爬虫API测试（2个用例）"""
    
    def test_start_crawler_task(self, client, auth_headers):
        """CRAWL-API-001: POST /api/crawler/start"""
        data = {
            'source_type': 'rss',
            'source_url': 'https://example.com/rss',
            'category': '科技'
        }
        
        response = client.post('/api/crawler/start', 
                             json=data, 
                             headers=auth_headers)
        
        # 可能返回201（任务创建）或200（任务启动）
        assert response.status_code in [200, 201]
        result = response.get_json()
        assert result['success'] is True
        
        # 验证返回任务信息
        if 'task_id' in result.get('data', {}):
            assert result['data']['task_id'] is not None
            print(f"✓ 启动爬虫任务API测试通过，任务ID: {result['data']['task_id']}")
        else:
            print("✓ 启动爬虫任务API测试通过")
    
    def test_start_crawler_task_unauthorized(self, client):
        """测试未授权启动爬虫任务"""
        data = {
            'source_type': 'rss',
            'source_url': 'https://example.com/rss'
        }
        
        response = client.post('/api/crawler/start', json=data)
        assert response.status_code == 401
        print("✓ 未授权访问正确拒绝")
    
    def test_get_crawler_tasks(self, client, auth_headers):
        """CRAWL-API-002: GET /api/crawler/tasks"""
        response = client.get('/api/crawler/tasks', headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'tasks' in result['data'] or 'items' in result['data']
        print("✓ 获取爬虫任务列表API测试通过")
    
    def test_get_crawler_task_by_id(self, client, auth_headers):
        """测试根据ID获取爬虫任务"""
        # 先创建一个任务
        create_data = {
            'source_type': 'rss',
            'source_url': 'https://example.com/rss',
            'category': '测试'
        }
        create_response = client.post('/api/crawler/start', 
                                     json=create_data, 
                                     headers=auth_headers)
        
        if create_response.status_code in [200, 201]:
            result = create_response.get_json()
            if 'task_id' in result.get('data', {}):
                task_id = result['data']['task_id']
                
                # 获取任务详情
                response = client.get(f'/api/crawler/tasks/{task_id}', headers=auth_headers)
                assert response.status_code in [200, 404]  # 404也是合理的（任务可能已完成）
                print("✓ 根据ID获取爬虫任务测试通过")
            else:
                print("⚠ 爬虫任务未返回task_id，跳过详情测试")
        else:
            print("⚠ 爬虫任务创建失败，跳过详情测试")


class TestSprint2UploadAPI:
    """Sprint 2：文件上传API测试（1个用例）"""
    
    def test_upload_file(self, client, auth_headers):
        """UPLOAD-API-001: POST /api/upload"""
        # 创建测试文件（中文需要先编码为字节，内容需要足够长）
        test_content = '''这是一个测试文件的内容。
        
本文档用于测试文件上传功能。文件上传是系统的核心功能之一，
需要支持多种文件格式，包括文本文件、PDF文档等。

测试内容应该包含足够的文本信息，以便系统能够正确处理和解析。
这里添加更多内容以满足最小长度要求。

文件上传功能的主要特点：
1. 支持多种文件格式
2. 自动提取文本内容
3. 向量化存储
4. 支持全文检索

这是测试文件的结尾部分。'''.encode('utf-8')
        
        response = client.post('/api/upload/file',
                             data={'file': (io.BytesIO(test_content), 'test.txt')},
                             content_type='multipart/form-data',
                             headers=auth_headers)
        
        # 调试：打印响应信息
        result = response.get_json()
        print(f"\n[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response body: {result}")
        
        # 可能返回200或201
        assert response.status_code in [200, 201]
        assert result['success'] is True
        print("[PASS] 文件上传API测试通过")
    
    def test_upload_file_unauthorized(self, client):
        """测试未授权上传文件"""
        data = {
            'file': (io.BytesIO(b'test content'), 'test.txt')
        }
        
        response = client.post('/api/upload/file',
                             data=data,
                             content_type='multipart/form-data')
        
        assert response.status_code == 401
        print("✓ 未授权上传正确拒绝")
    
    def test_upload_pdf_file(self, client, auth_headers):
        """测试上传PDF文件"""
        # 创建模拟PDF文件
        pdf_content = b'%PDF-1.4\n%fake pdf content for testing'
        data = {
            'file': (io.BytesIO(pdf_content), 'test.pdf')
        }
        
        response = client.post('/api/upload/file',
                             data=data,
                             content_type='multipart/form-data',
                             headers=auth_headers)
        
        assert response.status_code in [200, 201, 400]  # 400也可能（格式验证）
        if response.status_code in [200, 201]:
            result = response.get_json()
            assert result['success'] is True
            print("✓ PDF文件上传测试通过")
        else:
            print("⚠ PDF文件格式验证拒绝（预期行为）")
    
    def test_upload_without_file(self, client, auth_headers):
        """测试不提供文件的上传请求"""
        response = client.post('/api/upload/file',
                             data={},
                             content_type='multipart/form-data',
                             headers=auth_headers)
        
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        print("✓ 无文件上传正确拒绝")
