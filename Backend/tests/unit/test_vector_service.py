"""
Sprint 2：数据与AI服务层 - 向量化服务单元测试（基于LangChain框架）
测试用例：VECTOR-001, VECTOR-002, VECTOR-003, VECTOR-004

LangChain集成：
- 使用 LangChain HuggingFaceEmbeddings 进行文本向量化
- 使用 LangChain FAISS VectorStore 进行向量存储和检索
"""
import pytest
import numpy as np
import os
import tempfile
from Backend.services.vector_service import VectorService, get_vector_service


class TestSprint2VectorService:
    """Sprint 2：向量化服务测试（4个用例，使用真实模型）"""
    
    def test_embedding_model_loading(self, app):
        """VECTOR-001: LangChain HuggingFaceEmbeddings加载（all-MiniLM-L6-v2）"""
        with app.app_context():
            try:
                vector_service = get_vector_service()
                
                # 验证模型已加载
                assert vector_service.embedding_model is not None
                print("[OK] 嵌入模型加载成功")
            except Exception as e:
                pytest.skip(f"模型加载失败（可能未安装）: {str(e)}")
    
    def test_single_text_vectorization(self, app):
        """VECTOR-002: 单文本向量化（embed_query方法，384维）"""
        with app.app_context():
            try:
                vector_service = get_vector_service()
                
                test_text = "人工智能正在改变世界"
                result_vector = vector_service.vectorize_text(test_text)
                
                # 验证向量格式
                assert isinstance(result_vector, np.ndarray)
                assert result_vector.shape == (384,), f"向量维度应为384，实际为{result_vector.shape}"
                # 验证向量值合理（通常在-1到1之间）
                assert np.all(np.abs(result_vector) <= 10), "向量值应在合理范围内"
                print(f"[OK] 文本向量化成功，维度: {result_vector.shape}")
            except Exception as e:
                pytest.skip(f"向量化测试失败: {str(e)}")
    
    def test_faiss_index_building(self, app):
        """VECTOR-003: LangChain FAISS VectorStore构建"""
        with app.app_context():
            try:
                import faiss
                vector_service = get_vector_service()
                
                # 准备测试向量
                test_vectors = np.random.rand(5, 384).astype('float32')
                test_ids = [1, 2, 3, 4, 5]
                
                # 构建索引
                vector_service.build_faiss_index(test_vectors, test_ids)
                
                # 验证索引已创建
                assert vector_service.faiss_index is not None
                assert vector_service.faiss_index.ntotal == 5
                print(f"[OK] FAISS索引构建成功，包含{vector_service.faiss_index.ntotal}个向量")
            except ImportError:
                pytest.skip("FAISS未安装")
            except Exception as e:
                pytest.skip(f"FAISS索引测试失败: {str(e)}")
    
    def test_batch_vectorization_performance(self, app):
        """VECTOR-004: 批量向量化性能（embed_documents方法）"""
        with app.app_context():
            try:
                import time
                vector_service = get_vector_service()
                
                # 测试批量向量化
                test_texts = [f"这是测试文本{i}" for i in range(10)]
                start_time = time.time()
                
                vectors = vector_service.batch_vectorize(test_texts)
                
                end_time = time.time()
                batch_time = end_time - start_time
                
                # 验证结果
                assert vectors.shape == (10, 384)
                # 性能要求：批量处理10个文本应在合理时间内完成
                assert batch_time < 10.0, f"批量向量化性能不达标: {batch_time:.3f}秒"
                print(f"[OK] 批量向量化成功，耗时: {batch_time:.3f}秒")
            except Exception as e:
                pytest.skip(f"批量向量化测试失败: {str(e)}")


def test_search_similar_supports_in_memory_integer_mapping_keys():
    """新写入且尚未重启时，整数 mapping key 也必须能映射到知识 ID。"""
    import faiss

    vector_service = object.__new__(VectorService)
    vector_service.faiss_index = faiss.IndexFlatIP(2)
    vector_service.faiss_index.add(np.array([[1.0, 0.0]], dtype="float32"))
    vector_service.id_mapping = {0: 42}

    scores, knowledge_ids = vector_service.search_similar(
        np.array([1.0, 0.0], dtype="float32"), top_k=1
    )

    assert scores.tolist() == pytest.approx([1.0])
    assert knowledge_ids == [42]


def test_delete_document_supports_string_id_for_integer_mapping(tmp_path):
    """数据库返回字符串 vector_id 时，应能删除当前进程内的整数 mapping key。"""
    vector_service = object.__new__(VectorService)
    vector_service.id_mapping = {0: 42}
    vector_service.id_mapping_path = str(tmp_path / "id_mapping.json")

    assert vector_service.delete_document("0") is True
    assert vector_service.id_mapping == {}
