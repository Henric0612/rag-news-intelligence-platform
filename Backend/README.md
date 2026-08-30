# RAG News Intelligence Platform 后端

基于 Flask 3.x 的智能新闻问答系统后端服务。

## 技术栈

- **Web框架**: Flask 3.0.3
- **数据库**: SQLite 3.x / SQLAlchemy
- **认证**: JWT (Flask-JWT-Extended)
- **AI模型**: Sentence-Transformers, FAISS, Ollama
- **可选依赖**: Redis、Celery、APScheduler 存在于配置或依赖中，但当前运行时没有充分 wiring 证据，不属于 Phase B Compose 拓扑

## 项目结构

```
后端/
├── app.py                 # Flask 应用主入口
├── config.py             # 配置文件
├── requirements.txt      # Python 依赖（包含测试依赖）
├── init_db.py           # 数据库初始化脚本
├── run_tests.py         # 测试运行脚本
├── pytest.ini          # pytest 配置文件
├── models/              # 数据模型
│   ├── __init__.py
│   ├── user.py         # 用户模型
│   ├── knowledge.py    # 知识库模型
│   ├── search_history.py
│   ├── rss_source.py
│   └── crawl_task.py
├── services/           # 业务逻辑层
│   ├── __init__.py
│   ├── auth_service.py
│   └── knowledge_service.py
├── routes/             # 路由层
│   ├── __init__.py
│   ├── auth.py         # 认证路由
│   ├── knowledge.py    # 知识库路由
│   └── health.py       # 健康检查
├── utils/              # 工具类
│   ├── __init__.py
│   ├── jwt_utils.py
│   ├── text_utils.py
│   ├── response.py
│   └── decorators.py
├── tests/              # 测试套件（88个用例）
│   ├── unit/           # 单元测试 (37个)
│   ├── integration/    # 集成测试 (18个)
│   ├── api/            # API测试 (18个)
│   ├── e2e/            # E2E测试 (7个)
│   ├── performance/    # 性能测试 (6个)
│   ├── conftest.py     # 测试配置（本地离线模型）
│   └── README.md       # 测试文档
└── data/               # 数据目录（自动创建）
    ├── sqlite/         # SQLite数据库文件
    ├── faiss/          # FAISS索引文件
    └── uploads/        # 上传文件目录
```

## 快速开始

### 1. 创建Python虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 下载AI模型到本地（重要）

> **⚠️ 重要提示**：所有模型必须提前下载到本地。系统配置为**离线模式**，运行时不会联网下载或更新模型。

#### 3.1 Sentence Transformers 模型（必需）

```bash
# 激活虚拟环境后执行
# 下载嵌入模型（约90MB）
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# 下载重排模型（约120MB）
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

**缓存位置**：`~/.cache/huggingface/hub/`

#### 3.2 Ollama 和 qwen3:8b 模型（推荐）

```bash
# 1. 安装 Ollama（访问 https://ollama.ai/download）
# Windows: 下载安装包
# Linux/Mac: curl -fsSL https://ollama.ai/install.sh | sh

# 2. 下载 qwen3:8b 模型（约5GB，需要时间）
ollama pull qwen3:8b

# 3. 验证模型已安装
ollama list

# 4. 启动 Ollama 服务（后台运行）
ollama serve
```

**说明**：
- ✅ 有Ollama：完整功能（搜索 + RAG问答）
- ⚠️ 无Ollama：仅搜索功能可用

### 4. 初始化数据库

```bash
python init_db.py
```

### 5. 配置环境变量（可选）

复制 `env.example` 为 `.env` 并修改配置：

```bash
cp env.example .env
```

### 6. 运行应用

> **⚠️ 重要**：必须使用模块模式运行，不要直接运行 `python app.py`

```bash
# ✅ 方式1：在项目根目录运行（推荐）
cd 项目根目录
python -m Backend

# ✅ 方式2：在Backend目录运行
cd Backend
python -m Backend
```

**Windows PowerShell 示例**：
```powershell
cd "C:\path\to\rag-news-intelligence-platform"
.\Backend\venv\Scripts\Activate.ps1
python -m Backend
```

**为什么必须用模块模式？**
- ✅ 支持相对导入（`from .config import config`）
- ✅ 正确的包路径解析
- ✅ 测试和生产环境一致

服务将在 `http://localhost:5000` 启动。

## API文档

### 认证接口

#### 用户注册
```http
POST /api/auth/register
Content-Type: application/json

{
    "username": "string",
    "password": "string",
    "email": "string"
}
```

#### 用户登录
```http
POST /api/auth/login
Content-Type: application/json

{
    "username": "string",
    "password": "string"
}
```

#### 获取当前用户信息
```http
GET /api/auth/me
Authorization: Bearer {access_token}
```

### 知识库接口

#### 获取知识库列表
```http
GET /api/knowledge?page=1&size=20&category=politics
Authorization: Bearer {access_token}
```

#### 创建知识库条目
```http
POST /api/knowledge
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "title": "string",
    "content": "string",
    "category": "string",
    "source_type": "manual"
}
```

#### 获取统计信息
```http
GET /api/knowledge/stats
Authorization: Bearer {access_token}
```

### 智能搜索接口

#### 语义搜索
```http
POST /api/search/query
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "query": "string",
    "top_k": 20,
    "search_type": "semantic"
}
```

#### 搜索建议
```http
GET /api/search/suggestions?q={query}
Authorization: Bearer {access_token}
```

#### 搜索历史
```http
GET /api/search/history
Authorization: Bearer {access_token}
```

### RAG问答接口

#### 智能问答
```http
POST /api/rag/ask
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "query": "string",
    "top_k": 10,
    "enable_rerank": true,
    "enable_web_fallback": false,
    "stream": false
}
```

#### RAG健康检查
```http
GET /api/rag/health
```

### 健康检查

```http
GET /api/health
GET /api/ready?quick=true
GET /api/ready?quick=false
```

- `/api/health` 是进程 liveness；AI 暂时不可用时仍返回 200。
- quick readiness 检查数据库与基础配置，不触发 AI 初始化。
- full readiness 检查 embedding、reranker、Host Ollama 与 `qwen3:8b`，依赖不可用时返回 503。
- 非流式 RAG 的 AI 依赖失败返回 HTTP 503、`success:false` 与 `AI_DEPENDENCY_UNAVAILABLE`；SSE 返回结构化 `type:error` 事件。

## 默认账户

- 管理员账户
  - 用户名: `admin`
  - 密码: `admin123`

- 测试用户
  - 用户名: `testuser`
  - 密码: `test123`

## 开发指南

### 运行测试

```bash
# 运行所有测试
python run_tests.py

# 按类型运行
python run_tests.py --unit          # 单元测试 (37个)
python run_tests.py --integration   # 集成测试 (18个)
python run_tests.py --api           # API测试 (18个)
python run_tests.py --e2e           # E2E测试 (7个)
python run_tests.py --performance   # 性能测试 (6个)

# 按Sprint运行
python run_tests.py --sprint 2      # Sprint 2测试

# 快速测试（跳过性能和E2E）
python run_tests.py --quick

# 生成覆盖率报告
python run_tests.py --coverage

# 查看帮助
python run_tests.py --help
```

**测试详情**: 参见 [tests/README.md](tests/README.md)

### 代码格式化

```bash
black .
flake8 .
```

## 部署

### Docker Compose 本地容器运行

```bash
cd ..
cp .env.example .env
docker compose config
docker compose up -d --build --wait
```

主入口为 `http://127.0.0.1:3000`。Backend 的 `127.0.0.1:5000` 仅用于本地工程检查。Ollama 保留为 WSL host service，不在 Compose 中；SQLite、FAISS、mapping 与 uploads 统一持久化在 `rag_data` 命名卷。完整前置条件、生命周期与数据保留说明见根目录 `README.md`。

## 注意事项

1. 本地 demo 以外必须替换 `SECRET_KEY` 和 `JWT_SECRET_KEY` 示例值。
2. 当前 SQLite + FAISS + mapping 部署约束为 single worker / single replica。
3. Redis、Celery 与 APScheduler 未进入 Phase B 运行拓扑。
4. 项目是 production-oriented，但不是 production-ready。

## License

Copyright © 2025 RAG News Intelligence Platform Project
