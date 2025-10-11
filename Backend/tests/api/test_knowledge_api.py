"""
Sprint 2：数据与AI服务层 - 知识库API测试
测试用例：KNOW-API-001, KNOW-API-002, KNOW-API-003, KNOW-API-004
"""
import pytest


class TestSprint2KnowledgeAPI:
    """Sprint 2：知识库API测试（4个用例）"""
    
    def test_create_knowledge_item(self, client, auth_headers, sample_knowledge_data):
        """KNOW-API-001: POST /api/knowledge"""
        response = client.post('/api/knowledge', 
                             json=sample_knowledge_data, 
                             headers=auth_headers)
        
        assert response.status_code == 201
        result = response.get_json()
        assert result['success'] is True
        assert result['data']['title'] == sample_knowledge_data['title']
        assert result['data']['content'] == sample_knowledge_data['content']
        print("[PASS] 创建知识库条目API测试通过")
    
    def test_create_knowledge_item_unauthorized(self, client, sample_knowledge_data):
        """测试未授权创建知识库条目"""
        response = client.post('/api/knowledge', json=sample_knowledge_data)
        
        assert response.status_code == 401
        result = response.get_json()
        assert result['success'] is False
        print("[PASS] 未授权访问正确拒绝")
    
    def test_get_knowledge_items(self, client, auth_headers):
        """KNOW-API-002: GET /api/knowledge"""
        # 先创建一些测试数据
        for i in range(3):
            data = {
                'title': f'测试标题{i}',
                'content': f'测试内容{i}',
                'source_url': f'https://example.com/{i}',
                'source_type': 'web',
                'category': '测试分类',
                'tags': ['测试']
            }
            client.post('/api/knowledge', json=data, headers=auth_headers)
        
        # 获取列表
        response = client.get('/api/knowledge', headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'items' in result['data']
        assert 'total' in result['data']
        assert 'page' in result['data']
        assert len(result['data']['items']) >= 3
        print(f"[PASS] 获取知识库列表API测试通过，共{len(result['data']['items'])}条")
    
    def test_get_knowledge_item_by_id(self, client, auth_headers, sample_knowledge_data):
        """测试根据ID获取知识库条目"""
        # 先创建
        create_response = client.post('/api/knowledge', 
                                     json=sample_knowledge_data, 
                                     headers=auth_headers)
        item_id = create_response.get_json()['data']['id']
        
        # 获取
        response = client.get(f'/api/knowledge/{item_id}', headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['data']['id'] == item_id
        assert result['data']['title'] == sample_knowledge_data['title']
        print("[PASS] 根据ID获取知识库条目测试通过")
    
    def test_update_knowledge_item(self, client, auth_headers, sample_knowledge_data):
        """KNOW-API-003: PUT /api/knowledge/:id"""
        # 先创建
        create_response = client.post('/api/knowledge', 
                                     json=sample_knowledge_data, 
                                     headers=auth_headers)
        item_id = create_response.get_json()['data']['id']
        
        # 更新
        update_data = {
            'title': '更新后的标题',
            'content': '更新后的内容',
            'category': '更新后的分类'
        }
        response = client.put(f'/api/knowledge/{item_id}', 
                            json=update_data, 
                            headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['data']['title'] == '更新后的标题'
        assert result['data']['content'] == '更新后的内容'
        print("[PASS] 更新知识库条目API测试通过")
    
    def test_delete_knowledge_item(self, client, auth_headers, sample_knowledge_data):
        """KNOW-API-004: DELETE /api/knowledge/:id"""
        # 先创建
        create_response = client.post('/api/knowledge', 
                                     json=sample_knowledge_data, 
                                     headers=auth_headers)
        item_id = create_response.get_json()['data']['id']
        
        # 删除
        response = client.delete(f'/api/knowledge/{item_id}', headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        
        # 验证已删除
        get_response = client.get(f'/api/knowledge/{item_id}', headers=auth_headers)
        assert get_response.status_code == 404
        print("[PASS] 删除知识库条目API测试通过")
    
    def test_get_knowledge_items_with_pagination(self, client, auth_headers):
        """测试分页功能"""
        # 创建多条数据
        for i in range(15):
            data = {
                'title': f'分页测试{i}',
                'content': f'内容{i}',
                'source_url': f'https://example.com/{i}',
                'source_type': 'web'
            }
            client.post('/api/knowledge', json=data, headers=auth_headers)
        
        # 测试第一页
        response = client.get('/api/knowledge?page=1&per_page=10', headers=auth_headers)
        assert response.status_code == 200
        result = response.get_json()
        assert len(result['data']['items']) == 10
        assert result['data']['page'] == 1
        
        # 测试第二页
        response = client.get('/api/knowledge?page=2&per_page=10', headers=auth_headers)
        assert response.status_code == 200
        result = response.get_json()
        assert len(result['data']['items']) >= 5
        print("[PASS] 分页功能测试通过")
    
    def test_search_knowledge_items(self, client, auth_headers):
        """测试搜索功能"""
        # 创建测试数据
        test_data = [
            {'title': 'Python编程', 'content': 'Python是一种编程语言', 'source_url': 'http://example.com/1', 'source_type': 'web'},
            {'title': 'Java开发', 'content': 'Java是另一种编程语言', 'source_url': 'http://example.com/2', 'source_type': 'web'},
            {'title': 'Python数据分析', 'content': '使用Python进行数据分析', 'source_url': 'http://example.com/3', 'source_type': 'web'}
        ]
        for data in test_data:
            client.post('/api/knowledge', json=data, headers=auth_headers)
        
        # 搜索Python相关
        response = client.get('/api/knowledge?search=Python', headers=auth_headers)
        assert response.status_code == 200
        result = response.get_json()
        # 应该找到2条Python相关的记录
        python_items = [item for item in result['data']['items'] if 'Python' in item['title']]
        assert len(python_items) >= 2
        print(f"[PASS] 搜索功能测试通过，找到{len(python_items)}条Python相关记录")
