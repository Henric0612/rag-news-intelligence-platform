"""
Sprint 4：质量保证与交付 - 向量检索性能测试
测试用例：PERF-005
"""
import pytest
import time
import numpy as np
from Backend.services.vector_service import get_vector_service
from Backend.services.search_service import get_search_service
from Backend.models import db
from Backend.models.knowledge import KnowledgeItem


class TestSprint4VectorPerformance:
    """Sprint 4：向量检索性能测试（1个用例）"""
    
    def test_faiss_index_optimization(self, app):
        """PERF-005: FAISS索引优化（检索速度提升）"""
        with app.app_context():
            try:
                vector_service = get_vector_service()
                
                # 步骤1：测试向量化性能
                test_texts = [f'这是测试文本{i}，用于性能测试' for i in range(100)]
                
                start = time.time()
                vectors = vector_service.batch_vectorize(test_texts)
                vectorization_time = time.time() - start
                
                print(f"[PASS] 批量向量化100条文本耗时: {vectorization_time:.3f}秒")
                print(f"  平均每条: {vectorization_time/100*1000:.2f}ms")
                assert vectorization_time < 10.0, f"批量向量化应<10秒，实际: {vectorization_time:.3f}秒"
                
                # 步骤2：构建FAISS索引
                test_ids = list(range(100))
                
                start = time.time()
                vector_service.build_faiss_index(vectors, test_ids)
                index_build_time = time.time() - start
                
                print(f"[PASS] 构建FAISS索引耗时: {index_build_time:.3f}秒")
                assert index_build_time < 5.0, f"索引构建应<5秒，实际: {index_build_time:.3f}秒"
                
                # 步骤3：测试向量检索性能
                query_text = "测试查询文本"
                query_vector = vector_service.vectorize_text(query_text)
                
                # 多次检索测试
                search_times = []
                for _ in range(10):
                    start = time.time()
                    distances, knowledge_ids = vector_service.search_similar(query_vector, top_k=10)
                    search_time = time.time() - start
                    search_times.append(search_time * 1000)  # 转换为毫秒
                
                avg_search_time = sum(search_times) / len(search_times)
                max_search_time = max(search_times)
                
                print(f"[PASS] FAISS检索平均耗时: {avg_search_time:.2f}ms")
                print(f"  最大耗时: {max_search_time:.2f}ms")
                assert avg_search_time < 100, f"平均检索时间应<100ms，实际: {avg_search_time:.2f}ms"
                
                # 步骤4：测试不同top_k的性能
                for k in [5, 10, 20, 50]:
                    start = time.time()
                    distances, knowledge_ids = vector_service.search_similar(query_vector, top_k=k)
                    search_time = (time.time() - start) * 1000
                    
                    print(f"[PASS] Top-{k}检索耗时: {search_time:.2f}ms")
                    assert search_time < 200, f"Top-{k}检索应<200ms"
                
                print("[PASS] PERF-005: FAISS索引优化测试通过")
                
            except Exception as e:
                # 不要跳过测试，而是显示真实错误以便修复业务代码
                import traceback
                print(f"\n[FAIL] FAISS性能测试失败，错误详情：")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                print(f"堆栈跟踪:\n{traceback.format_exc()}")
                raise  # 重新抛出异常，让测试失败而不是跳过
    
    def test_embedding_model_performance(self, app):
        """测试嵌入模型性能"""
        with app.app_context():
            try:
                vector_service = get_vector_service()
                
                # 测试单文本向量化性能
                single_times = []
                for i in range(10):
                    text = f"这是第{i}条测试文本"
                    start = time.time()
                    vector = vector_service.vectorize_text(text)
                    single_time = (time.time() - start) * 1000
                    single_times.append(single_time)
                
                avg_single_time = sum(single_times) / len(single_times)
                print(f"[PASS] 单文本向量化平均耗时: {avg_single_time:.2f}ms")
                
                # 测试批量向量化性能
                batch_sizes = [10, 50, 100]
                for batch_size in batch_sizes:
                    texts = [f"批量测试文本{i}" for i in range(batch_size)]
                    
                    start = time.time()
                    vectors = vector_service.batch_vectorize(texts)
                    batch_time = time.time() - start
                    
                    per_item_time = (batch_time / batch_size) * 1000
                    print(f"[PASS] 批量{batch_size}条向量化耗时: {batch_time:.3f}秒 (平均{per_item_time:.2f}ms/条)")
                    
                    # 批量处理应该比单独处理快
                    assert per_item_time < avg_single_time, f"批量处理应该更快"
                
                print("[PASS] 嵌入模型性能测试通过")
                
            except Exception as e:
                # 不要跳过测试，而是显示真实错误以便修复业务代码
                import traceback
                print(f"\n[FAIL] 嵌入模型性能测试失败，错误详情：")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                print(f"堆栈跟踪:\n{traceback.format_exc()}")
                raise  # 重新抛出异常，让测试失败而不是跳过
    
    def test_semantic_search_end_to_end_performance(self, app):
        """测试端到端语义搜索性能"""
        with app.app_context():
            # 添加测试数据
            test_items = [
                KnowledgeItem(
                    title=f'性能测试文档{i}',
                    content=f'这是关于人工智能和机器学习的测试内容{i}' * 5,
                    source_url=f'http://example.com/perf{i}',
                    source_name='性能测试',
                    source_type='web',
                    category='科技'
                )
                for i in range(50)
            ]
            for item in test_items:
                db.session.add(item)
            db.session.commit()
            
            try:
                search_service = get_search_service()
                
                # 测试端到端搜索性能（包括向量化+检索+重排）
                queries = [
                    "人工智能",
                    "机器学习算法",
                    "深度学习应用",
                    "自然语言处理",
                    "计算机视觉"
                ]
                
                total_times = []
                for query in queries:
                    start = time.time()
                    results = search_service.semantic_search(query, top_k=10)
                    total_time = (time.time() - start) * 1000
                    total_times.append(total_time)
                    
                    print(f"[PASS] 查询'{query}'耗时: {total_time:.2f}ms")
                
                avg_total_time = sum(total_times) / len(total_times)
                print(f"[PASS] 端到端搜索平均耗时: {avg_total_time:.2f}ms")
                
                # 端到端搜索应该在合理时间内完成
                assert avg_total_time < 2000, f"端到端搜索应<2秒，实际: {avg_total_time:.2f}ms"
                
                print("[PASS] 端到端语义搜索性能测试通过")
                
            finally:
                # 清理测试数据
                for item in test_items:
                    db.session.delete(item)
                db.session.commit()
    
    def test_vector_index_scalability(self, app):
        """测试向量索引可扩展性"""
        with app.app_context():
            try:
                vector_service = get_vector_service()
                
                # 测试不同数据量下的索引性能
                data_sizes = [100, 500, 1000]
                
                for size in data_sizes:
                    # 生成测试向量
                    vectors = np.random.rand(size, 384).astype('float32')
                    ids = list(range(size))
                    
                    # 构建索引
                    start = time.time()
                    vector_service.build_faiss_index(vectors, ids)
                    build_time = time.time() - start
                    
                    # 测试检索
                    query_vector = np.random.rand(384).astype('float32')
                    start = time.time()
                    distances, knowledge_ids = vector_service.search_similar(query_vector, top_k=10)
                    search_time = (time.time() - start) * 1000
                    
                    print(f"[PASS] {size}条数据: 索引构建{build_time:.3f}秒, 检索{search_time:.2f}ms")
                    
                    # 验证性能随数据量的增长是合理的
                    assert search_time < 200, f"{size}条数据检索应<200ms"
                
                print("[PASS] 向量索引可扩展性测试通过")
                
            except Exception as e:
                # 不要跳过测试，而是显示真实错误以便修复业务代码
                import traceback
                print(f"\n[FAIL] 可扩展性测试失败，错误详情：")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                print(f"堆栈跟踪:\n{traceback.format_exc()}")
                raise  # 重新抛出异常，让测试失败而不是跳过
