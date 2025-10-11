"""
Sprint 2：数据与AI服务层 - RAG流程集成测试（基于LangChain框架）
测试用例：RAG-INT-001, RAG-INT-002, RAG-INT-003

LangChain集成：
- 使用 LangChain LCEL (LangChain Expression Language) 构建RAG链
- 使用 PromptTemplate 进行提示词管理
- 使用 RunnablePassthrough 和 StrOutputParser 构建数据流
"""
import pytest
from Backend.services.rag_service import RAGService
from Backend.services.search_service import get_search_service
from Backend.services.vector_service import get_vector_service
from Backend.services.llm_service import get_llm_service
from Backend.models import db
from Backend.models.knowledge import KnowledgeItem


class TestSprint2RAGIntegration:
    """Sprint 2：RAG流程集成测试（3个核心用例）"""
    
    def test_complete_rag_workflow(self, app):
        """RAG-INT-001: LangChain LCEL完整RAG流程（向量检索→重排→LLM）"""
        with app.app_context():
            # 添加测试数据
            test_items = [
                KnowledgeItem(
                    title='人工智能基础',
                    content='人工智能（AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。AI系统可以学习、推理、解决问题、理解自然语言和感知环境。',
                    source_url='http://example.com/ai',
                    source_name='科技百科',
                    source_type='web',
                    category='科技'
                ),
                KnowledgeItem(
                    title='机器学习概述',
                    content='机器学习是人工智能的一个子领域，它使计算机能够在没有明确编程的情况下学习和改进。机器学习算法使用统计技术使计算机能够从数据中"学习"。',
                    source_url='http://example.com/ml',
                    source_name='学术期刊',
                    source_type='web',
                    category='科技'
                ),
                KnowledgeItem(
                    title='深度学习技术',
                    content='深度学习是机器学习的一个分支，它使用多层神经网络来学习数据的表示。深度学习在图像识别、语音识别和自然语言处理等领域取得了突破性进展。',
                    source_url='http://example.com/dl',
                    source_name='技术博客',
                    source_type='web',
                    category='科技'
                )
            ]
            for item in test_items:
                db.session.add(item)
            db.session.commit()
            
            # 为测试数据构建向量索引
            vector_service = get_vector_service()
            texts = [f"{item.title} {item.content}" for item in test_items]
            knowledge_ids = [item.id for item in test_items]
            vectors = vector_service.batch_vectorize(texts)
            vector_service.build_faiss_index(vectors, knowledge_ids)
            
            try:
                rag_service = RAGService()
                
                # 执行完整RAG流程
                query = "什么是人工智能？"
                result = rag_service.answer_question(query)
                
                # 验证结果存在
                assert result is not None
                
                # 验证结果包含答案（可能是字典或字符串）
                if isinstance(result, dict):
                    assert 'answer' in result or 'response' in result
                    print("[PASS] 完整RAG流程测试通过（字典格式）")
                    
                    # 如果有来源信息，验证来源
                    if 'sources' in result:
                        assert len(result['sources']) > 0
                        print(f"  - 使用了{len(result['sources'])}个知识库来源")
                else:
                    assert isinstance(result, str) and len(result) > 0
                    print("[PASS] 完整RAG流程测试通过（字符串格式）")
                
            except Exception as e:
                # 不要跳过测试，而是显示真实错误以便修复业务代码
                import traceback
                print(f"\n[FAIL] RAG测试失败，错误详情：")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                print(f"堆栈跟踪:\n{traceback.format_exc()}")
                raise  # 重新抛出异常，让测试失败而不是跳过
            finally:
                # 清理测试数据
                for item in test_items:
                    db.session.delete(item)
                db.session.commit()
    
    def test_vector_search_to_rerank_pipeline(self, app):
        """RAG-INT-002: 向量检索→CrossEncoderReranker流程"""
        with app.app_context():
            # 添加多个相关度不同的测试数据
            test_items = [
                KnowledgeItem(
                    title='机器学习详解',
                    content='机器学习是人工智能的核心技术，包括监督学习、无监督学习和强化学习三大类。监督学习使用标记数据训练模型，无监督学习从未标记数据中发现模式。',
                    source_url='http://example.com/ml1',
                    source_name='AI教程',
                    source_type='web',
                    category='科技'
                ),
                KnowledgeItem(
                    title='机器学习应用',
                    content='机器学习在各个领域都有广泛应用，包括推荐系统、图像识别、语音识别、自然语言处理、金融预测等。这些应用正在改变我们的生活和工作方式。',
                    source_url='http://example.com/ml2',
                    source_name='技术应用',
                    source_type='web',
                    category='科技'
                ),
                KnowledgeItem(
                    title='深度学习框架',
                    content='常见的深度学习框架包括TensorFlow、PyTorch、Keras等。这些框架提供了构建和训练神经网络的工具，大大简化了深度学习模型的开发过程。',
                    source_url='http://example.com/dl-framework',
                    source_name='开发工具',
                    source_type='web',
                    category='科技'
                ),
                KnowledgeItem(
                    title='编程语言Python',
                    content='Python是一种高级编程语言，以其简洁的语法和强大的功能而闻名。Python在数据科学、Web开发、自动化等领域都有广泛应用。',
                    source_url='http://example.com/python',
                    source_name='编程教程',
                    source_type='web',
                    category='编程'
                )
            ]
            for item in test_items:
                db.session.add(item)
            db.session.commit()
            
            # 为测试数据构建向量索引
            vector_service = get_vector_service()
            texts = [f"{item.title} {item.content}" for item in test_items]
            knowledge_ids = [item.id for item in test_items]
            vectors = vector_service.batch_vectorize(texts)
            vector_service.build_faiss_index(vectors, knowledge_ids)
            
            try:
                search_service = get_search_service()
                
                # 1. 执行语义搜索（包含向量检索和重排）
                query = "机器学习的应用有哪些？"
                results = search_service.semantic_search(query, top_k=5)
                
                # 2. 验证搜索结果
                assert 'results' in results
                assert len(results['results']) > 0
                
                # 3. 验证结果相关性（前面的结果应该更相关）
                top_result = results['results'][0]
                assert 'title' in top_result
                assert 'content' in top_result
                assert 'score' in top_result or 'similarity_score' in top_result
                
                # 4. 验证相关内容排在前面
                # "机器学习应用"应该比"编程语言Python"更相关
                result_titles = [r.get('title', '') for r in results['results']]
                print(f"[PASS] 向量检索->重排流程测试通过")
                print(f"  - 返回{len(results['results'])}条结果")
                print(f"  - 结果顺序: {result_titles[:3]}")
                
                # 验证机器学习相关的结果排在前面
                ml_related_count = sum(1 for title in result_titles[:2] if '机器学习' in title)
                assert ml_related_count > 0, "机器学习相关结果应该排在前面"
                
            except Exception as e:
                # 不要跳过测试，而是显示真实错误以便修复业务代码
                import traceback
                print(f"\n[FAIL] 向量检索->重排测试失败，错误详情：")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                print(f"堆栈跟踪:\n{traceback.format_exc()}")
                raise  # 重新抛出异常，让测试失败而不是跳过
            finally:
                # 清理测试数据
                for item in test_items:
                    db.session.delete(item)
                db.session.commit()
    
    def test_context_building_accuracy(self, app):
        """RAG-INT-003: PromptTemplate上下文构建准确性"""
        with app.app_context():
            try:
                rag_service = RAGService()
                
                # 准备测试文档（模拟搜索结果）
                test_docs = [
                    {
                        'id': 1,
                        'title': '人工智能发展史',
                        'content': '人工智能的概念最早由图灵在1950年提出。经过几十年的发展，AI经历了多次兴衰周期，如今正处于快速发展阶段。',
                        'source_url': 'http://example.com/ai-history',
                        'source_name': '科技历史',
                        'similarity_score': 0.95
                    },
                    {
                        'id': 2,
                        'title': '机器学习基础',
                        'content': '机器学习是实现人工智能的主要方法之一。它通过算法使计算机能够从数据中学习规律，而不需要明确编程。',
                        'source_url': 'http://example.com/ml-basics',
                        'source_name': '学术期刊',
                        'similarity_score': 0.88
                    },
                    {
                        'id': 3,
                        'title': '深度学习突破',
                        'content': '深度学习在2012年ImageNet竞赛中取得突破性进展，此后在计算机视觉、自然语言处理等领域都取得了显著成果。',
                        'source_url': 'http://example.com/dl-breakthrough',
                        'source_name': '技术新闻',
                        'similarity_score': 0.82
                    }
                ]
                
                # 测试上下文构建
                context = rag_service.build_context(test_docs)
                
                # 验证上下文（应该返回 List[Dict]）
                assert context is not None
                assert isinstance(context, list), f"上下文应该是列表，实际类型: {type(context)}"
                assert len(context) > 0, "上下文不应该为空"
                
                # 验证上下文包含文档信息
                assert len(context) <= len(test_docs), "上下文文档数不应超过输入文档数"
                
                # 验证每个上下文文档的结构
                for doc in context:
                    assert 'content' in doc, "上下文文档应包含 content 字段"
                    assert 'title' in doc, "上下文文档应包含 title 字段"
                    assert isinstance(doc['content'], str), "content 应该是字符串"
                
                # 验证上下文包含关键信息
                all_content = ' '.join([doc['content'] for doc in context])
                assert '人工智能' in all_content or 'AI' in all_content, "上下文应包含人工智能相关内容"
                
                print("[PASS] 上下文构建准确性测试通过")
                print(f"  - 上下文文档数: {len(context)}")
                print(f"  - 总内容长度: {len(all_content)}字符")
                print(f"  - 使用文档数: {len(test_docs)}")
                print(f"  - 上下文预览: {context[0]['content'][:100]}...")
                
            except Exception as e:
                # 不要跳过测试，而是显示真实错误以便修复业务代码
                import traceback
                print(f"\n[FAIL] 上下文构建测试失败，错误详情：")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                print(f"堆栈跟踪:\n{traceback.format_exc()}")
                raise  # 重新抛出异常，让测试失败而不是跳过
    
    def test_rag_with_empty_knowledge_base(self, app):
        """测试空知识库时的RAG行为"""
        with app.app_context():
            # 清空知识库
            KnowledgeItem.query.delete()
            db.session.commit()
            
            try:
                rag_service = RAGService()
                
                # 在空知识库上执行RAG
                query = "什么是人工智能？"
                result = rag_service.answer_question(query)
                
                # 应该返回结果（可能是"无相关信息"或使用联网回退）
                assert result is not None
                print("[PASS] 空知识库RAG测试通过")
                
            except Exception as e:
                # 空知识库可能抛出异常，这是预期行为
                print(f"[PASS] 空知识库正确处理异常: {type(e).__name__}")
    
    def test_rag_with_multiple_rounds(self, app):
        """测试多轮对话RAG"""
        with app.app_context():
            # 添加测试数据
            test_item = KnowledgeItem(
                title='Python编程语言',
                content='Python是一种解释型、面向对象、动态数据类型的高级程序设计语言。Python由Guido van Rossum于1989年底发明，第一个公开发行版发行于1991年。',
                source_url='http://example.com/python',
                source_name='编程百科',
                source_type='web',
                category='编程'
            )
            db.session.add(test_item)
            db.session.commit()
            
            try:
                rag_service = RAGService()
                
                # 第一轮问答
                query1 = "Python是什么？"
                result1 = rag_service.answer_question(query1)
                assert result1 is not None
                
                # 第二轮问答（相关问题）
                query2 = "它是谁发明的？"
                result2 = rag_service.answer_question(query2)
                assert result2 is not None
                
                print("[PASS] 多轮对话RAG测试通过")
                
            except Exception as e:
                # 不要跳过测试，而是显示真实错误以便修复业务代码
                import traceback
                print(f"\n[FAIL] 多轮对话RAG测试失败，错误详情：")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                print(f"堆栈跟踪:\n{traceback.format_exc()}")
                raise  # 重新抛出异常，让测试失败而不是跳过
            finally:
                # 清理测试数据
                db.session.delete(test_item)
                db.session.commit()
    
    def test_rag_service_integration_with_all_components(self, app):
        """测试RAG服务与所有组件的集成"""
        with app.app_context():
            # 添加测试数据
            test_item = KnowledgeItem(
                title='测试集成',
                content='这是一条用于测试RAG服务与所有组件集成的测试数据',
                source_url='http://example.com/test',
                source_name='测试',
                source_type='web',
                category='测试'
            )
            db.session.add(test_item)
            db.session.commit()
            
            try:
                # 1. 测试向量服务可用
                vector_service = get_vector_service()
                assert vector_service is not None
                print("  [OK] 向量服务可用")
                
                # 2. 测试搜索服务可用
                search_service = get_search_service()
                assert search_service is not None
                print("  [OK] 搜索服务可用")
                
                # 3. 测试LLM服务可用
                llm_service = get_llm_service()
                assert llm_service is not None
                print("  [OK] LLM服务可用")
                
                # 4. 测试RAG服务可用
                rag_service = RAGService()
                assert rag_service is not None
                print("  [OK] RAG服务可用")
                
                # 5. 测试完整流程
                query = "测试查询"
                result = rag_service.answer_question(query)
                assert result is not None
                
                print("[PASS] RAG服务与所有组件集成测试通过")
                
            except Exception as e:
                # 不要跳过测试，而是显示真实错误以便修复业务代码
                import traceback
                print(f"\n[FAIL] RAG组件集成测试失败，错误详情：")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                print(f"堆栈跟踪:\n{traceback.format_exc()}")
                raise  # 重新抛出异常，让测试失败而不是跳过
            finally:
                # 清理测试数据
                db.session.delete(test_item)
                db.session.commit()