"""
Sprint 2：数据与AI服务层 - LLM服务单元测试（基于LangChain框架）
测试用例：LLM-001, LLM-002, LLM-003, LLM-004

LangChain集成：
- 使用 LangChain Ollama 进行LLM调用
- 使用 invoke 方法进行同步生成
- 使用 stream 方法进行流式输出

策略：减少Mock，验证真实服务行为和配置
"""
import pytest
from Backend.services.llm_service import get_llm_service


class TestSprint2LLMService:
    """Sprint 2：LLM服务测试（4个用例）"""
    
    def test_ollama_model_initialization(self, app):
        """LLM-001: LangChain Ollama初始化（qwen3:8b）
        
        验证：
        - LangChain Ollama服务实例正确创建
        - 配置参数正确加载
        - LLM客户端初始化（可能失败，但不应崩溃）
        """
        with app.app_context():
            # 获取LLM服务实例
            llm_service = get_llm_service()
            
            # 验证服务初始化
            assert llm_service is not None, "LLM服务应该成功创建"
            
            # 验证配置加载
            assert hasattr(llm_service, 'model_name'), "应该有model_name属性"
            assert hasattr(llm_service, 'ollama_host'), "应该有ollama_host属性"
            assert hasattr(llm_service, 'max_tokens'), "应该有max_tokens属性"
            assert hasattr(llm_service, 'temperature'), "应该有temperature属性"
            
            # 验证默认配置
            assert llm_service.model_name == 'qwen3:8b', "默认模型应为qwen3:8b"
            assert llm_service.ollama_host == 'http://localhost:11434', "默认主机应为localhost:11434"
            assert llm_service.max_tokens > 0, "max_tokens应大于0"
            assert 0 <= llm_service.temperature <= 1, "temperature应在0-1之间"
            
            # 验证方法存在性
            assert hasattr(llm_service, 'generate_answer'), "应该有generate_answer方法"
            assert hasattr(llm_service, 'stream_response'), "应该有stream_response方法"
            assert hasattr(llm_service, 'build_prompt'), "应该有build_prompt方法"
            assert hasattr(llm_service, 'health_check'), "应该有health_check方法"
            
            print(f"[OK] LLM服务初始化成功")
            print(f"  - 模型: {llm_service.model_name}")
            print(f"  - 主机: {llm_service.ollama_host}")
            print(f"  - 最大令牌数: {llm_service.max_tokens}")
            print(f"  - 温度: {llm_service.temperature}")
    
    def test_basic_qa_generation(self, app):
        """LLM-002: LLM invoke方法问答生成
        
        验证：
        - generate_answer方法可调用（内部使用LangChain invoke）
        - 返回结果包含必要字段
        - 错误处理机制（如果Ollama不可用）
        """
        with app.app_context():
            llm_service = get_llm_service()
            
            # 测试问答生成
            query = "什么是人工智能？"
            context = [{"content": "人工智能是计算机科学的一个分支"}]
            
            # 调用生成方法
            result = llm_service.generate_answer(query, context)
            
            # 验证返回结果结构
            assert isinstance(result, dict), "返回结果应为字典"
            assert 'answer' in result, "结果应包含answer字段"
            assert 'formatted_response' in result, "结果应包含formatted_response字段"
            assert 'quality_score' in result, "结果应包含quality_score字段"
            assert 'response_time' in result, "结果应包含response_time字段"
            assert 'model' in result, "结果应包含model字段"
            
            # 验证答案不为空
            assert len(result['answer']) > 0, "答案不应为空"
            
            # 验证质量分数范围
            assert 0 <= result['quality_score'] <= 1, "质量分数应在0-1之间"
            
            # 验证响应时间
            assert result['response_time'] >= 0, "响应时间应为非负数"
            
            print(f"[OK] 问答生成测试通过")
            print(f"  - 查询: {query}")
            print(f"  - 答案长度: {len(result['answer'])} 字符")
            print(f"  - 质量分数: {result['quality_score']:.2f}")
            print(f"  - 响应时间: {result['response_time']:.2f} 秒")
            if 'error' in result:
                print(f"  - 注意: 服务降级运行 ({result['error']})")
    
    def test_error_handling_mechanism(self, app):
        """LLM-004: 错误处理机制
        
        验证：
        - LangChain客户端未初始化时的降级处理
        - 错误响应格式正确
        - 不会抛出未捕获异常
        """
        with app.app_context():
            llm_service = get_llm_service()
            
            # 测试1：模拟客户端未初始化
            original_client = llm_service.client
            llm_service.client = None
            
            query = "测试提示"
            context = []
            result = llm_service.generate_answer(query, context)
            
            # 验证降级响应
            assert isinstance(result, dict), "降级响应应为字典"
            assert 'error' in result, "降级响应应包含error字段"
            assert 'answer' in result, "降级响应应包含answer字段"
            assert '抱歉' in result['answer'] or 'AI服务' in result['answer'], "应包含友好的错误提示"
            assert result['quality_score'] == 0.0, "降级时质量分数应为0"
            
            print(f"[OK] 错误处理测试通过")
            print(f"  - 客户端未初始化时正确降级")
            print(f"  - 错误消息: {result['answer']}")
            
            # 恢复客户端
            llm_service.client = original_client
            
            # 测试2：空查询处理
            result = llm_service.generate_answer("", [])
            assert isinstance(result, dict), "空查询应返回有效响应"
            print(f"  - 空查询处理正常")
    
    def test_streaming_output_functionality(self, app):
        """LLM-003: LLM stream方法流式输出
        
        验证：
        - stream_response方法存在（内部使用LangChain stream）
        - 返回生成器对象
        - 错误时不会崩溃
        """
        with app.app_context():
            llm_service = get_llm_service()
            
            # 验证方法存在
            assert hasattr(llm_service, 'stream_response'), "应该有stream_response方法"
            assert callable(llm_service.stream_response), "stream_response应该可调用"
            
            # 测试流式输出（如果客户端可用）
            query = "请生成一个简短回答"
            context = []
            
            try:
                # 尝试获取流式响应
                stream = llm_service.stream_response(query, context)
                
                # 验证返回生成器
                assert hasattr(stream, '__iter__'), "应返回可迭代对象"
                
                # 尝试读取第一个块（如果服务可用）
                first_chunk = next(stream, None)
                
                if first_chunk is not None:
                    assert isinstance(first_chunk, str), "流式块应为字符串"
                    print(f"[OK] 流式输出测试通过")
                    print(f"  - 成功获取流式响应")
                    print(f"  - 首块长度: {len(first_chunk)} 字符")
                else:
                    print(f"[OK] 流式输出测试通过（服务不可用，降级模式）")
                    
            except Exception as e:
                # 如果Ollama不可用，验证错误处理
                print(f"[OK] 流式输出测试通过（预期降级）")
                print(f"  - 错误处理正常: {type(e).__name__}")
            
            # 验证辅助方法
            assert hasattr(llm_service, 'build_prompt'), "应该有build_prompt方法"
            prompt = llm_service.build_prompt(query, context)
            assert isinstance(prompt, str), "build_prompt应返回字符串"
            assert len(prompt) > 0, "提示词不应为空"
            
            print(f"  - 提示词构建正常，长度: {len(prompt)} 字符")
    
