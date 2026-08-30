# RAG News Intelligence Platform - 前端界面

基于 Vue 3 + Vite + Element Plus 的现代化前端界面，采用科技极简风格设计。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **Element Plus** - Vue 3 组件库
- **Pinia** - Vue 状态管理
- **Vue Router** - Vue 官方路由
- **Axios** - HTTP 客户端

## 功能特性

### 已实现功能
- ✅ 用户认证（登录/注册）
- ✅ 知识库管理（CRUD 操作）
- ✅ 系统健康监控
- ✅ 响应式布局
- ✅ 暗色模式切换
- ✅ 路由守卫
- ✅ 状态管理
- ✅ 智能搜索（语义搜索 + 搜索建议）
- ✅ RAG问答系统（多轮对话）
- ✅ 搜索历史管理
- ✅ 向量服务状态监控
- ✅ LLM 服务状态监控
- ✅ 聊天界面（流式输出支持）
- ✅ 搜索结果展示（相关度评分）

### 占位功能（待后端实现）
- 🔄 数据分析面板
- 🔄 文件上传处理
- 🔄 批量数据导入

## 项目结构

```
Frontend/
├── src/
│   ├── api/               # API 接口
│   │   ├── request.js     # Axios 配置
│   │   ├── auth.js        # 认证接口
│   │   ├── knowledge.js   # 知识库接口
│   │   ├── search.js      # 搜索接口 ✅
│   │   ├── rag.js         # RAG问答接口 ✅
│   │   └── health.js      # 健康检查接口 ✅
│   ├── assets/            # 静态资源
│   │   └── styles/        # 样式文件
│   │       ├── variables.css  # CSS 变量
│   │       ├── theme.css      # 主题样式
│   │       └── global.css     # 全局样式
│   ├── composables/       # 组合式函数
│   │   └── useAsyncState.js   # 异步状态管理
│   ├── components/        # 公共组件
│   │   ├── Layout.vue     # 主布局
│   │   ├── AppHeader.vue  # 头部导航
│   │   ├── AppSidebar.vue # 侧边栏
│   │   ├── DarkModeToggle.vue # 暗色模式切换
│   │   ├── PageContainer.vue  # 页面容器
│   │   ├── LoadingSpinner.vue # 加载动画 ✅
│   │   └── EmptyState.vue     # 空状态 ✅
│   ├── router/            # 路由配置
│   │   └── index.js
│   ├── stores/            # 状态管理
│   │   ├── auth.js        # 认证状态 ✅
│   │   ├── knowledge.js   # 知识库状态 ✅
│   │   ├── search.js      # 搜索状态 ✅
│   │   └── chat.js        # 聊天状态 ✅
│   ├── views/             # 页面组件
│   │   ├── Login.vue      # 登录页
│   │   ├── Dashboard.vue  # 仪表板
│   │   ├── Knowledge.vue  # 知识库管理
│   │   ├── Search.vue     # 智能搜索 ✅
│   │   ├── Analytics.vue  # 数据分析（占位）
│   │   ├── Health.vue     # 系统健康
│   │   └── NotFound.vue   # 404 页面
│   ├── App.vue            # 根组件
│   └── main.js            # 入口文件
├── tests/                 # 测试文件（16个）
│   ├── unit/              # 单元测试（7个）
│   │   ├── test-environment.js        # 环境验证
│   │   ├── test-vue-framework.js      # Vue框架测试
│   │   ├── test-router-config.js      # 路由配置测试
│   │   ├── test-auth-store.js         # 认证Store测试
│   │   ├── test-search-store.js       # 搜索Store测试
│   │   ├── test-chat-store.js         # 聊天Store测试
│   │   └── test-knowledge-store.js    # 知识库Store测试
│   ├── integration/       # 集成测试（6个）
│   │   ├── test-auth-flow.js          # 认证流程测试
│   │   ├── test-search-flow.js        # 搜索流程测试
│   │   ├── test-chat-flow.js          # 问答流程测试
│   │   ├── test-knowledge-flow.js     # 知识库流程测试
│   │   ├── test-crawler-flow.js       # 爬虫流程测试
│   │   └── test-analytics-flow.js     # 分析流程测试
│   ├── e2e/               # E2E测试（1个，Playwright）
│   │   └── test-complete-flow.spec.js # 完整用户流程E2E测试
│   ├── performance/       # 性能测试（1个）
│   │   └── test-frontend-performance.js
│   ├── security/          # 安全测试（1个）
│   │   └── test-frontend-security.js
│   ├── setup.js           # 测试环境设置
│   └── README.md          # 测试文档
├── index.html             # HTML 模板
├── package.json           # 项目配置
├── vite.config.js         # Vite 配置
├── vitest.config.js       # 测试配置
├── run_tests.js           # 测试运行器
├── env.example            # 环境变量示例
└── README.md              # 项目文档
```

## 快速开始

### 环境要求

- Node.js >= 16.0.0
- npm >= 8.0.0

### 安装依赖

```bash
cd Frontend
npm install
```

### 环境配置

复制环境变量示例文件：

```bash
cp env.example .env
```

编辑 `.env` 文件，配置 API 基础地址：

```env
VITE_API_BASE_URL=/api
VITE_APP_TITLE=RAG News Intelligence Platform
VITE_APP_VERSION=1.0.0
```

`/api` 在 native Vite 工作流中由开发代理转发，在容器工作流中由 Caddy 转发到 `backend:5000`。

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000 (配置在 vite.config.js)

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

### Docker Compose 生产构建

容器运行使用 Vue production build + Caddy，不使用 Vite preview 或 Node 开发服务器。从仓库根目录运行：

```bash
docker compose up -d --build --wait
```

访问 `http://127.0.0.1:3000`。Caddy 提供静态文件、SPA fallback，并通过 `/api` 代理 Backend；Backend 暂时不可用时前端静态页面仍可启动和访问。

## 🧪 测试

### 运行所有测试

```bash
# 运行所有Vitest测试（单元+集成+性能+安全）
npm run test:all

# 或使用测试运行器
node run_tests.js
```

### 运行特定测试

```bash
# 单元测试（7个）
npm run test:unit:all

# 集成测试（6个）
npm run test:integration:all

# E2E测试（1个，需要Playwright）
npm run test:e2e          # 运行所有E2E测试
npm run test:e2e:ui       # UI模式（推荐）
npm run test:e2e:headed   # 有头模式
npm run test:e2e:report   # 查看报告

# 性能测试（1个）
npm run test:performance:all

# 安全测试（1个）
npm run test:security:all

# 测试覆盖率
npm run test:coverage

# 监听模式
npm run test:watch
```

### E2E测试说明

E2E测试使用 **Playwright** 进行真实浏览器测试，需要：

1. **安装Playwright**: `npm install -D @playwright/test && npx playwright install`
2. **启动后端**: 在仓库根目录运行 `python -m Backend` (http://localhost:5000)
3. **启动前端**: `cd Frontend && npm run dev` (http://localhost:3000)
4. **运行测试**: `npm run test:e2e`

详细说明请参考 [tests/README.md](./tests/README.md)

### 测试覆盖率

- **目标覆盖率**: 80%+
- **测试文件数**: 16个
  - 单元测试: 7个（Store、基础设施）
  - 集成测试: 6个（认证、搜索、问答、知识库、爬虫、分析）
  - E2E测试: 1个（完整用户流程，Playwright）
  - 性能测试: 1个（搜索、问答、页面加载）
  - 安全测试: 1个（XSS、CSRF、JWT）
- **覆盖范围**: Sprint 0-4 所有测试类型
- **报告位置**: `Frontend/coverage/index.html`

## 设计系统

### 色彩规范

- **主色调**: #3b82f6 (蓝色)
- **成功色**: #10b981 (绿色)
- **警告色**: #f59e0b (橙色)
- **错误色**: #ef4444 (红色)
- **信息色**: #3b82f6 (蓝色)

### 字体规范

- **主字体**: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto'
- **等宽字体**: 'SF Mono', Monaco, 'Cascadia Code'

### 间距规范

- **xs**: 4px
- **sm**: 8px
- **md**: 16px
- **lg**: 24px
- **xl**: 32px
- **2xl**: 48px
- **3xl**: 64px

### 圆角规范

- **sm**: 4px
- **md**: 8px
- **lg**: 12px
- **xl**: 16px
- **full**: 9999px

## 组件使用

### 页面容器

```vue
<template>
  <PageContainer title="页面标题" subtitle="页面描述">
    <!-- 页面内容 -->
  </PageContainer>
</template>
```

### 加载状态

```vue
<template>
  <LoadingSpinner text="加载中..." :size="24" />
</template>
```

### 空状态

```vue
<template>
  <EmptyState 
    title="暂无数据" 
    description="当前没有可显示的内容"
    icon="Document"
  >
    <template #actions>
      <el-button type="primary">添加数据</el-button>
    </template>
  </EmptyState>
</template>
```

## API 接口

### 认证接口

- `POST /api/auth/login` - 用户登录
- `POST /api/auth/register` - 用户注册
- `GET /api/auth/me` - 获取用户信息
- `POST /api/auth/logout` - 用户登出

### 知识库接口

- `GET /api/knowledge` - 获取知识库列表
- `GET /api/knowledge/:id` - 获取知识库详情
- `POST /api/knowledge` - 创建知识库条目
- `PUT /api/knowledge/:id` - 更新知识库条目
- `DELETE /api/knowledge/:id` - 删除知识库条目

### 搜索接口

- `POST /api/search/query` - 语义搜索
- `GET /api/search/suggestions` - 搜索建议
- `GET /api/search/history` - 搜索历史

### RAG问答接口

- `POST /api/rag/ask` - 智能问答
- `GET /api/rag/health` - RAG健康检查

### 健康检查接口

- `GET /api/health` - 健康检查
- `GET /api/ready` - 就绪检查

## 状态管理

所有 Store 使用 Pinia Composition API 编写，支持自动持久化和统一错误处理。

### 认证状态 (auth.js)

```javascript
const authStore = useAuthStore()

// 登录
await authStore.loginUser({ username, password })

// 登出
await authStore.logout()

// 检查认证状态
await authStore.checkAuth()
```

### 知识库状态 (knowledge.js)

```javascript
const knowledgeStore = useKnowledgeStore()

// 获取知识库列表
await knowledgeStore.fetchKnowledgeList()

// 创建知识库条目
await knowledgeStore.createKnowledgeItem(data)

// 更新知识库条目
await knowledgeStore.updateKnowledgeItem(id, data)
```

### 搜索状态 (search.js)

```javascript
const searchStore = useSearchStore()

// 执行搜索
await searchStore.performSearch(query, options)

// 获取搜索历史（自动持久化）
await searchStore.fetchSearchHistory()

// 获取搜索建议
await searchStore.fetchSearchSuggestions(query)

// 访问错误状态
console.log(searchStore.searchError)
```

### 聊天状态 (chat.js)

```javascript
const chatStore = useChatStore()

// 发送消息
await chatStore.sendMessage(query, options)

// 获取聊天历史（自动持久化）
const messages = chatStore.messages

// 清空聊天记录
chatStore.clearMessages()

// 导出聊天记录
const json = chatStore.exportAsJSON()
const text = chatStore.exportAsText()
```

## 路由配置

### 路由守卫

- 需要认证的路由会自动重定向到登录页
- 已登录用户访问登录页会重定向到首页
- 页面标题会根据路由自动更新

### 路由结构

```
/                    # 仪表板
/login              # 登录页
/knowledge          # 知识库管理
/search             # 智能搜索 ✅
/analytics          # 数据分析
/health             # 系统健康
```

## 开发指南

### 添加新页面

1. 在 `src/views/` 创建页面组件
2. 在 `src/router/index.js` 添加路由配置
3. 在 `src/components/AppSidebar.vue` 添加菜单项

### 添加新 API

1. 在 `src/api/` 创建接口文件
2. 在 `src/stores/` 添加状态管理
3. 在页面组件中调用

### 自定义主题

1. 修改 `src/assets/styles/variables.css` 中的 CSS 变量
2. 调整 `src/assets/styles/theme.css` 中的 Element Plus 主题
3. 更新 `src/assets/styles/global.css` 中的全局样式

## 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## 许可证

MIT License
