"""
Sprint 2：数据与AI服务层 - 文件处理服务单元测试
测试用例：FILE-001, FILE-002, FILE-003-1, FILE-003-2, FILE-003-3, FILE-003-4

测试原则：
1. 单元测试应该快速（<100ms/测试）
2. 隔离外部依赖（使用Mock）
3. 一个测试只测试一个功能点
4. 测试实际业务逻辑，而非仅检查方法存在性
"""
import pytest
import os
import tempfile
from Backend.services.file_service import FileService


class TestSprint2FileService:
    """Sprint 2：文件处理服务测试（6个用例）"""
    
    def test_pdf_text_extraction(self, app):
        """FILE-001: PDF文本提取 - 测试服务初始化和方法可用性"""
        with app.app_context():
            file_service = FileService()
            
            # 验证服务正确初始化
            assert file_service is not None, "FileService应该能正常初始化"
            assert os.path.exists(file_service.upload_dir), "上传目录应该已创建"
            
            # 验证核心方法存在且可调用
            assert hasattr(file_service, 'extract_file_content'), "应该有extract_file_content方法"
            assert callable(getattr(file_service, 'extract_file_content')), "extract_file_content应该可调用"
            
            # 验证支持的文件类型配置
            assert '.pdf' in file_service.SUPPORTED_EXTENSIONS, "应该支持PDF文件"
            assert '.txt' in file_service.SUPPORTED_EXTENSIONS, "应该支持TXT文件"
    
    def test_txt_file_upload(self, app):
        """FILE-002: TXT文件上传 - 测试TXT文件内容提取"""
        with app.app_context():
            file_service = FileService()
            
            # 创建临时TXT文件（最小化I/O操作）
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                test_content = '这是测试内容'
                f.write(test_content)
                temp_file = f.name
            
            try:
                # 测试文件内容提取
                result = file_service.extract_file_content(temp_file, '.txt')
                
                # 验证返回结构
                assert result is not None, "应该返回结果"
                assert isinstance(result, dict), "结果应该是字典"
                assert 'success' in result, "应该包含success字段"
                assert 'content' in result, "应该包含content字段"
                
                # 验证内容正确性
                assert result['success'] is True, "提取应该成功"
                assert test_content in result['content'], "应该包含原始内容"
                assert len(result['content']) > 0, "内容不应为空"
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
    
    def test_text_chunking_basic(self, app):
        """FILE-003-1: 文本分块 - 基本功能测试"""
        with app.app_context():
            file_service = FileService()
            
            # 测试基本分块功能
            text = "这是第一段文本。" * 25  # 200字符
            chunks = file_service.chunk_text(text, chunk_size=100, overlap=20)
            
            # 验证分块结果
            assert len(chunks) >= 2, "应该生成至少2个块"
            assert all(isinstance(c, str) for c in chunks), "所有块应该是字符串"
            assert all(len(c) > 0 for c in chunks), "所有块都应该有内容"
            assert all(len(c) <= 120 for c in chunks), "每个块不应超过chunk_size+20%"
    
    def test_text_chunking_edge_cases(self, app):
        """FILE-003-2: 文本分块 - 边界情况测试"""
        with app.app_context():
            file_service = FileService()
            
            # 测试1：短文本不分块
            short_text = "短文本"
            chunks_short = file_service.chunk_text(short_text, chunk_size=200)
            assert len(chunks_short) == 1, "短文本应该只有1个块"
            assert chunks_short[0] == short_text, "短文本内容应该保持不变"
            
            # 测试2：空文本处理
            empty_chunks = file_service.chunk_text("", chunk_size=200)
            assert empty_chunks == [], "空文本应该返回空列表"
            
            # 测试3：只有空格的文本
            whitespace_chunks = file_service.chunk_text("   ", chunk_size=200)
            assert whitespace_chunks == [], "只有空格的文本应该返回空列表"
    
    def test_text_chunking_overlap_validation(self, app):
        """FILE-003-3: 文本分块 - Overlap参数验证"""
        with app.app_context():
            file_service = FileService()
            
            # 测试overlap自动调整（防止内存爆炸）
            test_text = "测试文本。" * 30  # 150字符
            
            # overlap=100会被自动调整为50（chunk_size的一半）
            chunks = file_service.chunk_text(test_text, chunk_size=100, overlap=100)
            assert len(chunks) >= 1, "应该能正常分块"
            assert len(chunks) < 100, "不应该产生过多的块（说明overlap被正确调整）"
    
    def test_text_chunking_performance(self, app):
        """FILE-003-4: 文本分块 - 性能测试"""
        with app.app_context():
            file_service = FileService()
            
            # 测试大文本处理性能
            import time
            large_text = "这是一段文本。" * 500  # 约3000字符
            
            start_time = time.time()
            chunks = file_service.chunk_text(large_text, chunk_size=500, overlap=100)
            elapsed = time.time() - start_time
            
            # 验证性能要求
            assert elapsed < 0.1, f"处理3000字符应该在100ms内完成，实际耗时{elapsed*1000:.2f}ms"
            assert len(chunks) > 0, "应该生成分块"
            assert len(chunks) < 20, "不应该产生过多的块"
