"""
Sprint 3：应用功能层 - 前端界面E2E测试
测试用例：E2E-003, E2E-004
注意：这些测试主要验证后端API支持前端功能，真正的前端E2E测试应该在Frontend/tests/e2e/中
"""
import pytest


class TestSprint3FrontendE2E:
    """Sprint 3：前端界面E2E测试（2个用例）"""
    
    def test_search_interface_flow(self, client, auth_headers):
        """E2E-003: 智能搜索界面流程（后端API支持）"""
        # 模拟前端搜索界面的操作流程
        
        # 步骤1：用户输入搜索关键词
        search_query = "人工智能"
        
        # 步骤2：获取搜索建议
        suggestions_response = client.get(f'/api/search/suggestions?q={search_query[:2]}', 
                                        headers=auth_headers)
        
        assert suggestions_response.status_code == 200
        suggestions = suggestions_response.get_json()
        assert suggestions['success'] is True
        print(f"✓ 搜索建议获取成功，返回{len(suggestions['data'])}条建议")
        
        # 步骤3：执行搜索
        search_data = {
            'query': search_query,
            'top_k': 10
        }
        
        search_response = client.post('/api/search/query', 
                                    json=search_data, 
                                    headers=auth_headers)
        
        assert search_response.status_code == 200
        search_result = search_response.get_json()
        assert 'results' in search_result
        print(f"✓ 搜索执行成功，返回{search_result['total']}条结果")
        
        # 步骤4：用户可能点击某个搜索结果查看详情
        if search_result['total'] > 0:
            first_result = search_result['results'][0]
            if 'id' in first_result:
                detail_response = client.get(f'/api/knowledge/{first_result["id"]}', 
                                           headers=auth_headers)
                
                if detail_response.status_code == 200:
                    print("✓ 搜索结果详情获取成功")
        
        print("✓ E2E-003: 智能搜索界面流程测试通过")
    
    def test_qa_dialog_interface_flow(self, client, auth_headers):
        """E2E-004: 问答对话界面流程（后端API支持）"""
        # 模拟前端问答对话界面的操作流程
        
        # 步骤1：用户输入问题
        question = "什么是机器学习？"
        
        # 步骤2：发送问题到RAG API
        rag_data = {
            'query': question,
            'stream': False
        }
        
        rag_response = client.post('/api/rag/ask', 
                                 json=rag_data, 
                                 headers=auth_headers)
        
        assert rag_response.status_code == 200
        rag_result = rag_response.get_json()
        assert rag_result['success'] is True
        assert 'answer' in rag_result['data']
        
        print("✓ 问答请求成功")
        print(f"  问题: {question}")
        print(f"  答案长度: {len(rag_result['data']['answer'])}字符")
        
        # 步骤3：显示来源信息
        sources = rag_result['data']['sources']
        print(f"  来源数量: {len(sources)}")
        
        # 步骤4：用户可能继续提问（多轮对话）
        follow_up_question = "它有哪些应用？"
        
        follow_up_data = {
            'query': follow_up_question,
            'stream': False
        }
        
        follow_up_response = client.post('/api/rag/ask', 
                                        json=follow_up_data, 
                                        headers=auth_headers)
        
        assert follow_up_response.status_code == 200
        follow_up_result = follow_up_response.get_json()
        assert follow_up_result['success'] is True
        
        print("✓ 多轮对话支持正常")
        
        # 步骤5：用户可能查看搜索历史
        # 注意：这需要有搜索历史API
        
        print("✓ E2E-004: 问答对话界面流程测试通过")
    
    def test_complete_user_journey(self, client, auth_headers):
        """测试完整用户旅程"""
        # 步骤1：用户登录（已通过auth_headers完成）
        print("✓ 用户已登录")
        
        # 步骤2：浏览知识库
        list_response = client.get('/api/knowledge', headers=auth_headers)
        assert list_response.status_code == 200
        print("✓ 浏览知识库")
        
        # 步骤3：执行搜索
        search_response = client.post('/api/search/query',
                                    json={'query': '测试', 'top_k': 5},
                                    headers=auth_headers)
        assert search_response.status_code == 200
        print("✓ 执行搜索")
        
        # 步骤4：进行问答
        rag_response = client.post('/api/rag/ask',
                                  json={'query': '什么是人工智能？', 'stream': False},
                                  headers=auth_headers)
        assert rag_response.status_code == 200
        print("✓ 进行问答")
        
        # 步骤5：查看数据分析
        analytics_response = client.get('/api/analytics/clustering', headers=auth_headers)
        assert analytics_response.status_code == 200
        print("✓ 查看数据分析")
        
        print("✓ 完整用户旅程测试通过")
    
    def test_interface_error_handling(self, client, auth_headers):
        """测试界面错误处理"""
        # 测试搜索空查询
        search_response = client.post('/api/search/query',
                                    json={'query': '', 'top_k': 5},
                                    headers=auth_headers)
        assert search_response.status_code == 400
        print("✓ 搜索空查询错误处理正确")
        
        # 测试问答空查询
        rag_response = client.post('/api/rag/ask',
                                  json={'query': '', 'stream': False},
                                  headers=auth_headers)
        assert rag_response.status_code == 400
        print("✓ 问答空查询错误处理正确")
        
        # 测试访问不存在的知识库条目
        detail_response = client.get('/api/knowledge/99999', headers=auth_headers)
        assert detail_response.status_code == 404
        print("✓ 不存在条目错误处理正确")
        
        print("✓ 界面错误处理测试通过")
