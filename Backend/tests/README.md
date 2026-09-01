# 后端测试文档 v3.1

## 📋 测试概述

基于**敏捷开发指导书v3.md**重构的测试套件，按Sprint组织，覆盖所有10项考核要求。

**LangChain框架集成**：
- 向量化服务使用 LangChain HuggingFaceEmbeddings
- 检索服务使用 LangChain CrossEncoderReranker
- LLM服务使用 LangChain Ollama
- RAG服务使用 LangChain LCEL (Expression Language)

**当前测试模块统计（按 repository tree）**：
- Unit：13 个模块
- Integration：5 个模块
- API：8 个模块
- E2E：6 个模块
- Performance：4 个模块
- 总计：36 个 pytest 测试模块
- pytest 配置覆盖率门槛：80%

以上数字是版本化 `test_*.py` 文件的 module inventory，不是 pytest collected case 数或通过数。下方 Sprint 场景目录保留为历史测试设计映射；其中的场景 ID 与状态图标不应被解读为本次执行结果。

---

## 📁 测试结构

```
Backend/tests/
├── __init__.py                    # 测试包初始化
├── conftest.py                    # 测试配置和夹具
├── unit/                          # 13 个测试模块
│   ├── test_environment.py
│   ├── test_auth_service.py
│   ├── test_models.py
│   ├── test_crawler_service.py
│   ├── test_file_service.py
│   ├── test_vector_service.py
│   ├── test_search_service.py
│   ├── test_llm_service.py
│   ├── test_rag_failure_contract.py
│   ├── test_knowledge_service.py
│   ├── test_email_service.py
│   ├── test_web_search_service.py
│   └── test_analytics_service.py
├── integration/                   # 5 个测试模块
│   ├── test_auth_integration.py
│   ├── test_rag_integration.py
│   ├── test_model_integration.py
│   ├── test_email_integration.py
│   └── test_web_search_integration.py
├── api/                           # 8 个测试模块
│   ├── test_auth_api.py
│   ├── test_health_api.py
│   ├── test_knowledge_api.py
│   ├── test_crawler_api.py
│   ├── test_search_api.py
│   ├── test_rag_api.py
│   ├── test_model_status_api.py
│   └── test_analytics_api.py
├── e2e/                           # 6 个测试模块
│   ├── test_search_e2e.py
│   ├── test_rag_qa_e2e.py
│   ├── test_frontend_e2e.py
│   ├── test_knowledge_e2e.py
│   ├── test_crawler_e2e.py
│   └── test_analytics_e2e.py
└── performance/                   # 4 个测试模块
    ├── test_api_performance.py
    ├── test_database_performance.py
    ├── test_vector_performance.py
    └── test_concurrency_performance.py
```

---

## 🎯 按Sprint组织的测试

### Sprint 0：项目准备与设计

**测试文件**：`unit/test_environment.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| ENV-001 | Python 3.11+环境验证 | ✅ |
| ENV-002 | Node.js 18+环境验证 | ✅ |
| FRAME-001 | Flask应用初始化 | ✅ |
| FRAME-002 | Vue3应用初始化验证 | ✅ |
| DB-001 | SQLite数据库连接 | ✅ |
| DB-002 | FAISS向量库初始化 | ✅ |

**运行命令**：
```bash
cd Backend
python -m pytest tests/unit/test_environment.py -v
```

---

### Sprint 1：基础设施层

#### 单元测试

**测试文件**：
- `unit/test_auth_service.py`（4个）
- `unit/test_models.py`（3个）

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| AUTH-001 | 用户注册（有效数据） | ✅ |
| AUTH-002 | 用户登录（正确凭据） | ✅ |
| AUTH-003 | JWT Token生成验证 | ✅ |
| AUTH-004 | 密码加密验证 | ✅ |
| MODEL-001 | User模型CRUD | ✅ |
| MODEL-002 | KnowledgeItem模型CRUD | ✅ |
| MODEL-003 | SearchHistory模型CRUD | ✅ |

#### 集成测试

**测试文件**：`integration/test_auth_integration.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| AUTH-INT-001 | 完整认证流程 | ✅ |
| AUTH-INT-002 | Token刷新机制 | ✅ |

#### API测试

**测试文件**：`api/test_auth_api.py`, `api/test_health_api.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| AUTH-API-001 | POST /api/auth/register | ✅ |
| AUTH-API-002 | POST /api/auth/login | ✅ |
| AUTH-API-003 | POST /api/auth/refresh | ✅ |
| HEALTH-API-001 | GET /api/health | ✅ |
| HEALTH-API-002 | GET /api/ready | ✅ |

**运行命令**：
```bash
# 单元测试
python -m pytest tests/unit/test_auth_service.py tests/unit/test_models.py -v

# 集成测试
python -m pytest tests/integration/test_auth_integration.py -v

# API测试
python -m pytest tests/api/test_auth_api.py tests/api/test_health_api.py -v
```

---

### Sprint 2：数据与AI服务层

#### 2.1 数据采集服务

**测试文件**：
- `unit/test_crawler_service.py`（2个）
- `unit/test_file_service.py`（6个）

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| CRAWL-001 | RSS订阅解析（服务初始化+方法验证） | ✅ |
| CRAWL-002 | 网页内容抓取（服务初始化+HTTP配置） | ✅ |
| FILE-001 | PDF文本提取（服务初始化+文件类型支持） | ✅ |
| FILE-002 | TXT文件内容提取（返回结构+内容正确性） | ✅ |
| FILE-003-1 | 文本分块-基本功能（滑动窗口算法） | ✅ |
| FILE-003-2 | 文本分块-边界情况（短文本/空文本/空格） | ✅ |
| FILE-003-3 | 文本分块-Overlap验证（参数自动调整） | ✅ |
| FILE-003-4 | 文本分块-性能测试（<100ms/3000字符） | ✅ |

#### 2.2 向量化与检索（基于LangChain框架）

**测试文件**：`unit/test_vector_service.py`, `unit/test_search_service.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| VECTOR-001 | LangChain HuggingFaceEmbeddings加载 | ✅ |
| VECTOR-002 | 单文本向量化（embed_query） | ✅ |
| VECTOR-003 | LangChain FAISS VectorStore构建 | ✅ |
| VECTOR-004 | 批量向量化（embed_documents） | ✅ |
| SEARCH-001 | 语义检索功能 | ✅ |
| SEARCH-002 | LangChain CrossEncoderReranker | ✅ |
| SEARCH-003 | 检索性能<200ms | ✅ |
| SEARCH-004 | 空结果处理 | ✅ |

#### 2.3 LLM与RAG（基于LangChain框架）

**测试文件**：`unit/test_llm_service.py`, `integration/test_rag_integration.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| LLM-001 | LangChain Ollama初始化（qwen3:8b） | ✅ |
| LLM-002 | LLM invoke方法问答生成 | ✅ |
| LLM-003 | LLM stream方法流式输出 | ✅ |
| LLM-004 | 错误处理机制 | ✅ |
| RAG-INT-001 | LangChain LCEL完整RAG流程 | ✅ |
| RAG-INT-002 | 向量检索→CrossEncoderReranker | ✅ |
| RAG-INT-003 | PromptTemplate上下文构建 | ✅ |
| RAG-INT-004 | 空知识库RAG行为 | ✅ |
| RAG-INT-005 | 多轮对话RAG | ✅ |
| RAG-INT-006 | RAG组件集成 | ✅ |
| RAG-INT-007 | 相关性排序验证 | ✅ |

#### 2.4 知识库管理

**测试文件**：`unit/test_knowledge_service.py`, `api/test_knowledge_api.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| KNOW-API-001 | POST /api/knowledge | ✅ |
| KNOW-API-002 | GET /api/knowledge | ✅ |
| KNOW-API-003 | PUT /api/knowledge/:id | ✅ |
| KNOW-API-004 | DELETE /api/knowledge/:id | ✅ |

#### 2.5 数据采集API

**测试文件**：`api/test_crawler_api.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| CRAWL-API-001 | POST /api/crawler/start | ✅ |
| CRAWL-API-002 | GET /api/crawler/tasks | ✅ |
| UPLOAD-API-001 | POST /api/upload | ✅ |

#### 2.6 Sprint 2 E2E测试

**测试文件**：`e2e/test_search_e2e.py`, `e2e/test_rag_qa_e2e.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| E2E-001 | 智能搜索完整流程 | ✅ |
| E2E-002 | RAG问答完整流程 | ✅ |

**运行命令**：
```bash
# 单元测试
python -m pytest tests/unit/test_crawler_service.py -v
python -m pytest tests/unit/test_file_service.py -v
python -m pytest tests/unit/test_vector_service.py -v
python -m pytest tests/unit/test_search_service.py -v
python -m pytest tests/unit/test_llm_service.py -v

# 集成测试
python -m pytest tests/integration/test_rag_integration.py -v

# API测试
python -m pytest tests/api/test_knowledge_api.py -v
python -m pytest tests/api/test_crawler_api.py -v
python -m pytest tests/api/test_search_api.py -v
python -m pytest tests/api/test_rag_api.py -v

# E2E测试
python -m pytest tests/e2e/test_search_e2e.py -v
python -m pytest tests/e2e/test_rag_qa_e2e.py -v
```

---

### Sprint 3：应用功能层

#### 3.1 前端界面E2E

**测试文件**：`e2e/test_frontend_e2e.py`, `e2e/test_knowledge_e2e.py`, `e2e/test_crawler_e2e.py`, `e2e/test_analytics_e2e.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| E2E-003 | 智能搜索界面流程 | ✅ |
| E2E-004 | 问答对话界面流程 | ✅ |
| E2E-005 | 知识库管理界面流程 | ✅ |
| E2E-006 | 爬虫管理界面流程 | ✅ |
| E2E-007 | 数据分析页面展示 | ✅ |

#### 3.2 入库邮件通知

**测试文件**：`unit/test_email_service.py`, `integration/test_email_integration.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| EMAIL-001 | SMTP邮件发送 | ✅ |
| EMAIL-002 | 邮件模板渲染 | ✅ |
| EMAIL-INT-001 | 入库触发邮件通知 | ✅ |
| EMAIL-INT-002 | 邮件失败不阻塞主流程 | ✅ |
| EMAIL-INT-003 | 邮件内容必需字段 | ✅ |

#### 3.3 联网查询回退

**测试文件**：`unit/test_web_search_service.py`, `integration/test_web_search_integration.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| WEB-001 | 百度搜索API调用 | ✅ |
| WEB-002 | 搜索结果解析 | ✅ |
| WEB-INT-001 | 本地无结果→联网搜索 | ✅ |
| WEB-INT-002 | RAG联网回退 | ✅ |
| WEB-INT-003 | 联网搜索结果格式 | ✅ |
| WEB-INT-004 | 中文查询联网搜索 | ✅ |

#### 3.4 数据聚类分析

**测试文件**：`unit/test_analytics_service.py`, `api/test_analytics_api.py`

| 测试用例ID | 测试描述 | 状态 |
|-----------|---------|------|
| ANALYTICS-001 | KMeans聚类算法 | ✅ |
| ANALYTICS-002 | TF-IDF关键词提取 | ✅ |
| ANALYTICS-003 | Top10关键词统计 | ✅ |
| ANALYTICS-API-001 | GET /api/analytics/clustering | ✅ |

**运行命令**：
```bash
# Sprint 3单元测试
python -m pytest tests/unit/test_email_service.py -v
python -m pytest tests/unit/test_web_search_service.py -v
python -m pytest tests/unit/test_analytics_service.py -v

# Sprint 3集成测试
python -m pytest tests/integration/test_email_integration.py -v
python -m pytest tests/integration/test_web_search_integration.py -v

# Sprint 3 API测试
python -m pytest tests/api/test_analytics_api.py -v

# Sprint 3 E2E测试
python -m pytest tests/e2e/test_frontend_e2e.py -v
python -m pytest tests/e2e/test_knowledge_e2e.py -v
python -m pytest tests/e2e/test_crawler_e2e.py -v
python -m pytest tests/e2e/test_analytics_e2e.py -v
```

---

### Sprint 4：质量保证与交付

#### 4.1 API性能测试

**测试文件**：`performance/test_api_performance.py`

| 测试用例ID | 测试描述 | 目标指标 | 状态 |
|-----------|---------|---------|------|
| PERF-001 | API响应时间 | < 500ms (95%请求) | ⏳ |
| PERF-002 | 搜索响应时间 | < 200ms | ⏳ |
| PERF-003 | RAG问答响应 | < 30s | ⏳ |

#### 4.2 数据库性能测试

**测试文件**：`performance/test_database_performance.py`

| 测试用例ID | 测试描述 | 目标指标 | 状态 |
|-----------|---------|---------|------|
| PERF-004 | 数据库查询优化 | 索引优化完成 | ⏳ |

#### 4.3 向量检索性能测试

**测试文件**：`performance/test_vector_performance.py`

| 测试用例ID | 测试描述 | 目标指标 | 状态 |
|-----------|---------|---------|------|
| PERF-005 | FAISS索引优化 | 检索速度提升 | ⏳ |

#### 4.4 并发性能测试

**测试文件**：`performance/test_concurrency_performance.py`

| 测试用例ID | 测试描述 | 目标指标 | 状态 |
|-----------|---------|---------|------|
| PERF-006 | 并发性能测试 | 支持100+并发 | ⏳ |

**运行命令**：
```bash
# 运行所有性能测试
python -m pytest tests/performance/ -v

# 运行单个性能测试
python -m pytest tests/performance/test_api_performance.py -v
python -m pytest tests/performance/test_database_performance.py -v
python -m pytest tests/performance/test_vector_performance.py -v
python -m pytest tests/performance/test_concurrency_performance.py -v
```

---

## 🚀 快速开始

### 安装依赖
```bash
cd Backend
pip install -r requirements.txt
```

### 运行所有测试
```bash
python run_tests.py
```

### 运行特定Sprint测试
```bash
# Sprint 0
python -m pytest tests/unit/test_environment.py -v

# Sprint 1
python -m pytest tests/unit/test_auth_service.py tests/unit/test_models.py -v
python -m pytest tests/integration/test_auth_integration.py -v
python -m pytest tests/api/test_auth_api.py -v

# Sprint 2
python -m pytest tests/unit/test_vector_service.py tests/unit/test_search_service.py tests/unit/test_llm_service.py -v
python -m pytest tests/integration/test_rag_integration.py -v
python -m pytest tests/api/test_search_api.py tests/api/test_rag_api.py -v

# Sprint 3
python -m pytest tests/unit/test_email_service.py -v
python -m pytest tests/unit/test_web_search_service.py -v
python -m pytest tests/unit/test_analytics_service.py -v
python -m pytest tests/integration/test_email_integration.py -v
python -m pytest tests/integration/test_web_search_integration.py -v
python -m pytest tests/e2e/test_frontend_e2e.py -v
python -m pytest tests/e2e/test_knowledge_e2e.py -v
python -m pytest tests/e2e/test_crawler_e2e.py -v
python -m pytest tests/e2e/test_analytics_e2e.py -v

# Sprint 4
python -m pytest tests/performance/ -v
```

### 生成覆盖率报告
```bash
python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term
```

---

## 📊 测试覆盖率目标

| Sprint | 单元测试 | 集成测试 | API测试 | E2E测试 |
|--------|---------|---------|---------|---------|
| Sprint 0 | 100% | N/A | N/A | N/A |
| Sprint 1 | > 80% | > 60% | 100% | N/A |
| Sprint 2 | > 80% | > 60% | 100% | 核心流程 |
| Sprint 3 | > 80% | > 60% | 100% | 核心流程 |
| Sprint 4 | > 80% | > 70% | 100% | 全覆盖 |

---

## 🎯 考核要求覆盖映射

| 序号 | 考核要求 | 相关测试用例 | 状态 |
|-----|---------|-------------|------|
| 1 | 定时任务+RSS/网页抓取 | CRAWL-001, CRAWL-002, CRAWL-API-001 | ✅ |
| 2 | Ollama部署qwen3:8b | LLM-001, LLM-002, LLM-003 | ✅ |
| 3 | 本地知识库+嵌入+重排 | VECTOR-001~004, SEARCH-001~004 | ✅ |
| 4 | API写入知识库 | KNOW-API-001~004 | ✅ |
| 5 | 入库邮件通知 | EMAIL-001, EMAIL-002, EMAIL-INT-001 | ✅ |
| 6 | 用户登录 | AUTH-001~004, AUTH-INT-001~002 | ✅ |
| 7 | 知识库管理 | KNOW-API-001~004, E2E-005 | ✅ |
| 8 | 语义查询 | SEARCH-001~004, E2E-001 | ✅ |
| 9 | 联网查询回退 | WEB-001, WEB-002, WEB-INT-001 | ✅ |
| 10 | 数据聚类分析 | ANALYTICS-001~003, E2E-007 | ✅ |

---

## 🔧 测试配置

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

### 测试夹具（conftest.py）
- `app`: Flask测试应用实例
- `client`: Flask测试客户端
- `auth_headers`: 认证请求头
- `sample_knowledge_data`: 示例知识库数据
- `setup_test_environment`: 全局测试环境配置（自动使用）

### 🔒 本地离线模型配置

**重要**: 所有测试都配置为使用**本地离线模型**，不会联网下载或更新模型。

#### 自动配置
测试启动时自动设置以下环境变量：
```python
HF_HUB_OFFLINE=1          # 禁用HuggingFace Hub联网
TRANSFORMERS_OFFLINE=1    # 禁用Transformers联网
HF_DATASETS_OFFLINE=1     # 禁用Datasets联网
```

#### 所需本地模型
1. **嵌入模型**: `sentence-transformers/all-MiniLM-L6-v2`
2. **重排模型**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
3. **LLM模型**: `qwen3:8b` (Ollama)

#### 模型准备
运行测试前，请确保已下载所需模型到本地。参见: [Backend/README.md - 下载AI模型](../README.md#3-下载ai模型到本地重要)

---

## 📝 测试最佳实践

### 1. 测试命名规范
- 测试文件：`test_*.py`
- 测试类：`Test*`
- 测试方法：`test_*`

### 2. 测试结构（AAA模式）
```python
def test_function_name():
    # Arrange - 准备测试数据
    # Act - 执行被测试的功能
    # Assert - 验证结果
```

### 3. 减少Mock使用
- 优先使用真实服务和模型
- 仅在必要时Mock外部依赖
- 保证测试的真实性和价值

### 4. 测试数据管理
- 使用夹具创建测试数据
- 每个测试独立，不依赖其他测试
- 测试后清理数据（finally块）

---

## 🔄 持续改进

### 测试质量指标
- 测试覆盖率 > 80%
- 测试执行时间 < 5分钟
- 测试稳定性 > 95%
- 无过度Mock

### 测试维护
- 定期更新测试用例
- 重构时同步更新测试
- 监控测试执行结果
- 及时修复失败测试

---

## 📚 相关文档

- **敏捷开发指导书**：[敏捷开发指导书_v3.md](../../Docs/敏捷开发指导书_v3.md)
- **测试计划文档**：[测试计划文档_v3.md](../../Docs/测试计划文档_v3.md)
- **概要设计文档**：[概要设计文档_v2.md](../../Docs/概要设计文档_v2.md)
- **技术架构文档**：[技术架构文档.md](../../Docs/技术架构文档.md)

---

**文档版本**：v3.1（基于敏捷Sprint + 测试拆分优化）  
**创建时间**：2025-01-06  
**最后更新**：2025-01-08  
**对齐文档**：敏捷开发指导书_v3.md、测试计划文档_v3.md  
**测试执行状态**：本文档不发布当前 collected/passed case 数；实际结果必须以相应环境中的 pytest 输出为准。

---

## 🎊 测试套件重构总结

### 重构成果

本次测试套件全面重构，实现了以下目标：

#### 1. **统一命名规范** ✅
所有测试类都遵循`TestSprint{N}{ServiceName}{TestType}`命名规范：
- 单元测试：`TestSprint1AuthService`
- 集成测试：`TestSprint2RAGIntegration`
- API测试：`TestSprint3AnalyticsAPI`
- E2E测试：`TestSprint3FrontendE2E`
- 性能测试：`TestSprint4APIPerformance`

#### 2. **职责清晰** ✅
- **36 个测试模块**，每个文件职责单一
- 按Sprint组织，便于追溯和维护
- 按测试类型分类，结构清晰
- 单一服务原则：1个服务 = 1个测试文件

#### 3. **模块覆盖范围** ✅
- Unit、integration、API、E2E 与 performance 五类 pytest 模块均存在
- 新增的 `unit/test_rag_failure_contract.py` 已纳入当前 inventory
- 具体 case collection 与通过状态不在静态文档中推断

#### 4. **质量保证** ✅
- 减少Mock使用，使用真实服务
- 完善的数据清理（finally块）
- 详细的测试输出（✓标记）
- 合理的性能断言

### 测试文件映射

| 测试类型 | 模块数 | Sprint分布 |
|---------|------:|-----------|
| 单元测试 | 13 | Sprint 0-3 |
| 集成测试 | 5 | Sprint 1-3 |
| API测试 | 8 | Sprint 1-3 |
| E2E测试 | 6 | Sprint 2-3 |
| 性能测试 | 4 | Sprint 4 |
| **总计** | **36** | **全覆盖** |

### 关键改进

1. **拆分混合文件**
   - `test_auth_api.py` → 拆分为3个独立文件
   - `test_ai_e2e.py` → 拆分为6个独立文件
   - `test_sprint3_features.py` → 拆分为3个独立文件
   - `test_crawler_service.py` → 拆分为2个独立文件（爬虫+文件）

2. **新增缺失测试**
   - 集成测试：邮件集成、联网搜索集成
   - E2E测试：前端界面、知识库、爬虫、数据分析
   - 性能测试：数据库性能、向量性能、并发性能

3. **增强测试深度**
   - RAG集成测试从3个扩展到7个
   - 每个E2E测试包含多个子场景
   - 性能测试覆盖多个维度

### 测试执行

```bash
# 运行所有测试
python -m pytest tests/ -v

# 按类型运行
python -m pytest tests/unit/ -v          # 单元测试
python -m pytest tests/integration/ -v   # 集成测试
python -m pytest tests/api/ -v           # API测试
python -m pytest tests/e2e/ -v           # E2E测试
python -m pytest tests/performance/ -v   # 性能测试

# 按Sprint运行
python -m pytest tests/unit/test_environment.py -v  # Sprint 0
python -m pytest tests/unit/test_auth_service.py tests/integration/test_auth_integration.py -v  # Sprint 1
python -m pytest tests/unit/test_vector_service.py tests/integration/test_rag_integration.py -v  # Sprint 2
python -m pytest tests/unit/test_email_service.py tests/e2e/test_frontend_e2e.py -v  # Sprint 3
python -m pytest tests/performance/ -v  # Sprint 4

# 生成覆盖率报告
python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term
```

### 下一步计划

- [ ] 完成Sprint 4性能测试
- [ ] 运行完整测试套件
- [ ] 生成测试覆盖率报告
- [ ] 修复发现的问题
- [ ] 更新测试文档

---

**文档版本**：v3.1（基于LangChain框架集成）  
**最后更新**：2025-01-08  
**重要更新**：
- 更新测试用例描述以反映LangChain框架集成
- 向量化服务测试：LangChain HuggingFaceEmbeddings + FAISS VectorStore
- 检索服务测试：LangChain CrossEncoderReranker
- LLM服务测试：LangChain Ollama (invoke + stream)
- RAG集成测试：LangChain LCEL + PromptTemplate
- 所有测试用例保持向后兼容，验证LangChain集成后的功能正常性
