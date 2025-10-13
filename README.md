# XU-News-AI-RAG
基于AI的新闻RAG系统

## 项目结构
- Backend/ - 后端API服务（Flask + SQLAlchemy）
- Frontend/ - 前端界面（Vue 3 + Element Plus）
- Product Prototype/ - 产品原型
- Docs/ - 项目文档
- .gitignore - Git忽略文件配置

## 快速开始

### 环境要求
- **后端**: Python 3.13+
- **前端**: Node.js 18+
- **AI模型**: Ollama (可选，用于RAG问答)

### 后端服务（模块模式，推荐）
```bash
# 1. 创建并激活虚拟环境
cd Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 下载AI模型到本地（重要）
# 嵌入模型（约90MB）
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
# 重排模型（约120MB）
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# 4. 安装并启动Ollama（可选，用于RAG问答）
# 访问 https://ollama.ai/download 下载安装
ollama pull qwen3:8b  # 下载模型（约5GB）
ollama serve          # 启动服务

# 5. 初始化数据库
python init_db.py

# 6. 启动后端服务（在项目根目录）
cd ..
python -m Backend
```

后端服务将在 `http://localhost:5000` 启动

### 前端界面
```bash
cd Frontend
npm install

# 配置环境变量（可选）
cp env.example .env
# 编辑 .env 文件，设置 VITE_API_BASE_URL=http://localhost:5000

# 启动开发服务器
npm run dev
```

访问 `http://localhost:3000` 查看前端界面

### 默认账户
- **管理员**: 用户名 `admin` / 密码 `admin123`
- **测试用户**: 用户名 `testuser` / 密码 `test123`

## 🧪 测试

### 后端测试
```bash
cd Backend
# 安装依赖（包含测试依赖）
pip install -r requirements.txt

# 运行所有测试
python run_tests.py

# 运行特定测试
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
```

### 前端测试
```bash
cd Frontend
# 安装依赖
npm install

# 运行所有测试
node run_tests.js

# 按类型运行
npm run test:unit          # 单元测试（9个）
npm run test:integration   # 集成测试（5个）
npm run test:e2e           # E2E测试（6个）
npm run test:coverage      # 覆盖率报告
```

### 测试覆盖率
- **后端**: 40个单元测试 + 18个集成测试 + 18个API测试 + 7个E2E测试 + 6个性能测试 = **89个测试用例**
- **前端**: 7个单元测试 + 6个集成测试 + 1个E2E测试 + 1个性能测试 + 1个安全测试 = **16个测试用例**
- **总计**: **105个测试用例**，覆盖率 > 80%
- 后端报告: `Backend/htmlcov/index.html`
- 前端报告: `Frontend/coverage/index.html`

## 技术栈

### 后端
- **框架**: Python 3.13 + Flask 3.0.3
- **数据库**: SQLite 3.x + SQLAlchemy 2.0.35
- **向量数据库**: FAISS 1.8.0
- **AI框架**: LangChain 0.1.0+ (RAG框架)
- **嵌入模型**: Sentence-Transformers (all-MiniLM-L6-v2)
- **重排模型**: CrossEncoder (ms-marco-MiniLM-L-6-v2)
- **LLM**: Ollama + Qwen3:8b
- **任务调度**: APScheduler 3.10.4 + Celery 5.3.6
- **缓存**: Redis 5.0.1
- **测试**: pytest 8.3.3
- **爬虫**: BeautifulSoup4 4.12.3 + Requests 2.31.0

### 前端
- **框架**: Vue 3.4.0 + Vite 5.0.8
- **UI组件**: Element Plus 2.4.4
- **状态管理**: Pinia 2.1.7 + pinia-plugin-persistedstate 3.2.1
- **路由**: Vue Router 4.2.5
- **HTTP客户端**: Axios 1.6.2
- **Markdown渲染**: markdown-it 14.1.0
- **代码高亮**: highlight.js 11.11.1
- **安全**: DOMPurify 3.2.7
- **测试**: Vitest 1.6.1 + Playwright (E2E)

## 功能特性

### 核心功能（10项考核要求）
1. ✅ **定时任务+RSS/网页抓取** - APScheduler定时任务 + RSS订阅 + 网页爬虫
2. ✅ **Ollama部署qwen3:8b** - 本地LLM服务 + 流式输出支持
3. ✅ **本地知识库+嵌入+重排** - FAISS向量库 + LangChain框架 + CrossEncoder重排
4. ✅ **API写入知识库** - RESTful API + 文件上传 + 批量操作
5. ✅ **入库邮件通知** - SMTP邮件服务 + 异步发送
6. ✅ **用户登录** - JWT认证 + 密码加密 + Token刷新
7. ✅ **知识库管理** - CRUD操作 + 筛选排序 + 批量删除
8. ✅ **语义查询** - 向量检索 + 语义搜索 + 搜索建议
9. ✅ **联网查询回退** - 百度搜索API + 智能回退机制
10. ✅ **数据聚类分析** - KMeans聚类 + TF-IDF + Top10关键词

### 扩展功能
- ✅ **智能问答系统** - RAG问答 + 多轮对话 + 流式输出
- ✅ **搜索历史管理** - 历史记录 + 搜索统计
- ✅ **系统健康监控** - 实时状态 + 模型状态检查
- ✅ **响应式前端界面** - Vue 3 + Element Plus + 暗色模式
- ✅ **完整的测试套件** - 105个测试用例 + 80%+覆盖率
- ✅ **账户安全** - 密码重置 + 邮箱验证 + Token黑名单
- ✅ **内容质量优化** - 短内容智能补全 + 质量评分

## 项目架构

```
XU-News-AI-RAG/
├── Backend/              # 后端服务
│   ├── models/          # 数据模型（8个模型）
│   ├── services/        # 业务逻辑（17个服务）
│   ├── routes/          # API路由（8个路由）
│   ├── utils/           # 工具函数
│   ├── tests/           # 测试套件（89个测试）
│   └── data/            # 数据存储
│       ├── sqlite/      # SQLite数据库
│       ├── faiss/       # FAISS向量索引
│       └── uploads/     # 上传文件
├── Frontend/            # 前端界面
│   ├── src/
│   │   ├── api/        # API接口（9个）
│   │   ├── components/ # Vue组件（13个）
│   │   ├── views/      # 页面视图（10个）
│   │   ├── stores/     # Pinia状态管理（4个）
│   │   └── router/     # 路由配置
│   └── tests/          # 测试套件（16个测试）
├── Docs/               # 项目文档
│   ├── 产品需求文档_v2.md
│   ├── 技术架构文档.md
│   ├── 概要设计文档_v2.md
│   ├── 测试计划文档_v3.md
│   └── 敏捷开发指导书_v3.md
└── Product Prototype/  # 产品原型
```

## 开发指南

### 后端开发
详见 [Backend/README.md](Backend/README.md)

**关键服务**：
- `auth_service.py` - 用户认证
- `knowledge_service.py` - 知识库管理
- `vector_service.py` - 向量化（LangChain HuggingFaceEmbeddings）
- `search_service.py` - 语义搜索（LangChain CrossEncoderReranker）
- `llm_service.py` - LLM服务（LangChain Ollama）
- `rag_service.py` - RAG问答（LangChain LCEL）
- `crawler_service.py` - 爬虫服务
- `analytics_service.py` - 数据分析

### 前端开发
详见 [Frontend/README.md](Frontend/README.md)

**关键页面**：
- `/login` - 登录页
- `/` - 仪表板
- `/knowledge` - 知识库管理
- `/search` - 智能搜索
- `/analytics` - 数据分析
- `/health` - 系统健康

### 测试文档
- **后端测试**: [Backend/tests/README.md](Backend/tests/README.md) - 89个测试用例
- **前端测试**: [Frontend/tests/README.md](Frontend/tests/README.md) - 16个测试用例

## 重要说明

### AI模型配置
⚠️ **所有AI模型必须提前下载到本地**，系统运行在**离线模式**：
- 嵌入模型：`sentence-transformers/all-MiniLM-L6-v2` (~90MB)
- 重排模型：`cross-encoder/ms-marco-MiniLM-L-6-v2` (~120MB)
- LLM模型：`qwen3:8b` (~5GB，通过Ollama安装)

模型缓存位置：`~/.cache/huggingface/hub/`

### 环境配置
- 后端配置：复制 `Backend/env.example` 为 `Backend/.env`
- 前端配置：复制 `Frontend/env.example` 为 `Frontend/.env`
- 关键配置项：
  - `SECRET_KEY` - Flask密钥
  - `JWT_SECRET_KEY` - JWT密钥
  - `SMTP_USERNAME` / `SMTP_PASSWORD` - 邮件服务（可选）
  - `OLLAMA_HOST` - Ollama服务地址

### 生产部署注意事项
1. 修改所有密钥（SECRET_KEY, JWT_SECRET_KEY）
2. 使用PostgreSQL替代SQLite
3. 配置Redis用于缓存和任务队列
4. 启用HTTPS
5. 配置反向代理（Nginx/Apache）
6. 设置环境变量而非.env文件
7. 进行安全审计和性能测试

## 许可证
MIT License
