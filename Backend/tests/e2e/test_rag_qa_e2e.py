"""
Sprint 2：数据与AI服务层 - RAG问答E2E测试
测试用例：E2E-002
"""
import pytest
import time


class TestSprint2RAGQaE2E:
    """Sprint 2：RAG问答E2E测试（1个用例）"""
    
    def test_rag_qa_complete_flow(self, client, auth_headers):
        """E2E-002: RAG问答完整流程"""
        # 步骤1：执行RAG问答
        rag_data = {
            'query': '请详细解释人工智能的发展历程和主要里程碑',
            'stream': False
        }
        
        start_time = time.time()
        rag_response = client.post('/api/rag/ask', 
                                 json=rag_data, 
                                 headers=auth_headers)
        end_time = time.time()
        
        assert rag_response.status_code == 200
        rag_result = rag_response.get_json()
        assert rag_result['success'] is True
        
        # 验证RAG结果结构
        assert 'data' in rag_result
        assert 'answer' in rag_result['data']
        assert 'sources' in rag_result['data']
        assert 'response_time' in rag_result['data']
        assert 'query' in rag_result['data']
        
        print("✓ RAG问答执行成功")
        
        # 步骤2：获取上下文信息
        context_data = {
            'documents': [
                {'content': '人工智能是计算机科学的一个分支', 'title': 'AI定义'},
                {'content': '机器学习是AI的重要组成部分', 'title': '机器学习'},
                {'content': '深度学习是机器学习的一个子领域', 'title': '深度学习'}
            ],
            'max_length': 2000
        }
        
        context_response = client.post('/api/rag/context', 
                                     json=context_data, 
                                     headers=auth_headers)
        
        assert context_response.status_code == 200
        context_result = context_response.get_json()
        assert context_result['success'] is True
        assert 'context' in context_result['data']
        
        print(f"✓ 上下文构建成功，长度: {context_result['data'].get('context_length', len(context_result['data']['context']))}字符")
        
        # 步骤3：验证RAG性能
        response_time = end_time - start_time
        assert response_time < 30.0, f"RAG响应时间过长: {response_time}秒"
        
        print(f"✓ RAG性能达标，响应时间: {response_time:.3f}秒")
        
        # 步骤4：验证答案质量
        answer = rag_result['data']['answer']
        assert isinstance(answer, str), "答案应该是字符串"
        assert len(answer) > 0, "答案不能为空"
        
        print(f"✓ 答案生成成功，长度: {len(answer)}字符")
        
        # 步骤5：验证来源信息
        sources = rag_result['data']['sources']
        assert isinstance(sources, list), "来源信息格式错误"
        
        if sources:
            source = sources[0]
            assert 'title' in source or 'content' in source, "来源缺少必要字段"
            print(f"✓ 来源信息完整，共{len(sources)}个来源")
        else:
            print("⚠ 知识库为空，无来源信息")
        
        print("✓ E2E-002: RAG问答完整流程测试通过")
    
    def test_rag_with_web_fallback_flow(self, client, auth_headers):
        """测试RAG联网回退流程"""
        rag_data = {
            'query': '2025年最新的量子计算突破',
            'stream': False,
            'enable_web_fallback': True
        }
        
        response = client.post('/api/rag/ask', 
                             json=rag_data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        
        print("✓ RAG联网回退流程测试通过")
    
    def test_rag_streaming_flow(self, client, auth_headers):
        """测试RAG流式输出流程"""
        rag_data = {
            'query': '什么是机器学习？',
            'stream': True
        }
        
        response = client.post('/api/rag/ask', 
                             json=rag_data, 
                             headers=auth_headers)
        
        # 流式响应可能返回200或其他状态码
        assert response.status_code in [200, 201]
        
        print("✓ RAG流式输出流程测试通过")
    
    def test_complete_rag_workflow(self, client, auth_headers):
        """测试完整RAG工作流程"""
        # 步骤1：搜索相关文档
        search_data = {
            'query': '机器学习算法分类',
            'top_k': 3
        }
        
        search_response = client.post('/api/search/query', 
                                    json=search_data, 
                                    headers=auth_headers)
        assert search_response.status_code == 200
        
        # 步骤2：基于搜索结果进行RAG问答
        rag_data = {
            'query': '基于搜索结果，请解释机器学习的主要算法分类',
            'stream': False
        }
        
        rag_response = client.post('/api/rag/ask', 
                                 json=rag_data, 
                                 headers=auth_headers)
        assert rag_response.status_code == 200
        
        # 步骤3：验证整体性能
        search_result = search_response.get_json()
        rag_result = rag_response.get_json()
        
        total_time = 0
        if 'response_time' in search_result:
            total_time += search_result['response_time']
        if 'response_time' in rag_result.get('data', {}):
            total_time += rag_result['data']['response_time']
        
        print(f"✓ 完整RAG工作流程测试通过，总耗时: {total_time:.3f}秒")
    
    def test_rag_error_handling(self, client, auth_headers):
        """测试RAG错误处理"""
        # 测试空查询
        invalid_data = {
            'query': '',
            'stream': False
        }
        
        response = client.post('/api/rag/ask', 
                             json=invalid_data, 
                             headers=auth_headers)
        
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        
        print("✓ RAG错误处理测试通过")
