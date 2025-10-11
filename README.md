# XU-News-AI-RAG
基于AI的新闻RAG系统

## 项目结构
- Backend/ - 后端API服务（Flask + SQLAlchemy）
- Frontend/ - 前端界面（Vue 3 + Element Plus）
- Product Prototype/ - 产品原型
- Docs/ - 项目文档
- .gitignore - Git忽略文件配置

## 快速开始

### 后端服务（模块模式，推荐）
```bash
# 在项目根目录下创建并激活虚拟环境
cd Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 回到项目根目录，以包模块方式启动
cd ..
python -m Backend
```

### 前端界面
```bash
cd Frontend
npm install
npm run dev
```

访问 http://localhost:3000 查看前端界面

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
- **后端**: 43个单元测试 + 15个集成测试 + 17个API测试 + 7个E2E测试
- **前端**: 9个单元测试 + 5个集成测试 + 6个E2E测试 + 性能/安全测试
- **总计**: 87个测试套件，覆盖率 > 80%
- 后端报告: `Backend/htmlcov/index.html`
- 前端报告: `Frontend/coverage/index.html`

## 技术栈

### 后端
- Python 3.13
- Flask 3.0.3
- SQLAlchemy 2.0.35
- SQLite 3.x
- FAISS 1.8.0
- Ollama (LLM)
- pytest 8.3.3

### 前端
- Vue 3.4.0
- Vite 5.0.8
- Element Plus 2.4.4
- Pinia 2.1.7
- Vue Router 4.2.5
- Axios 1.6.2

## 功能特性

### 已实现（满足所有10项考核要求）
- ✅ 用户认证系统（注册/登录/JWT认证）
- ✅ 知识库管理（CRUD操作、筛选、批量删除）
- ✅ 文件上传处理（PDF/TXT/DOC/DOCX/RTF）
- ✅ RSS爬虫服务（定时任务、网页抓取）
- ✅ 智能搜索（语义搜索 + FAISS向量检索）
- ✅ 向量化服务（all-MiniLM-L6-v2 + 重排模型）
- ✅ LLM问答服务（Ollama + Qwen3:8b + RAG）
- ✅ 智能问答系统（多轮对话、流式输出）
- ✅ 入库邮件通知（自动发送通知邮件）
- ✅ 联网搜索回退（百度搜索API，返回前3条）
- ✅ 数据聚类分析（KMeans + Top10关键词）
- ✅ 搜索历史管理
- ✅ 系统健康监控（实时状态）
- ✅ 响应式前端界面（暗色模式）
- ✅ 完整的测试套件（单元/集成/E2E测试）

## 开发指南

### 后端开发
详见 [Backend/README.md](Backend/README.md)

### 前端开发
详见 [Frontend/README.md](Frontend/README.md)

### 测试文档
详见 [Backend/tests/README.md](Backend/tests/README.md) 和 [Frontend/tests/README.md](Frontend/tests/README.md)

## 许可证
MIT License
