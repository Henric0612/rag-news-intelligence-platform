# 前端测试文档

## 📋 测试计划对应关系

本测试套件严格按照 [测试计划文档_v3.md](../../Docs/测试计划文档_v3.md) 中的要求进行设计和实现。

### Sprint 0：项目准备与设计 ✅
- **ENV-002**: Node.js 18+环境验证 → `unit/test-environment.js`
- **FRAME-002**: Vue3应用初始化 → `unit/test-vue-framework.js`

### Sprint 1：基础设施层 ✅
- **AUTH-001~004**: 用户认证功能 → `unit/test-auth-store.js`
- **AUTH-INT-001~002**: 完整认证流程 → `integration/test-auth-flow.js`

### Sprint 2：数据与AI服务层 ✅
- **SEARCH-001~004**: 语义检索功能 → `unit/test-search-store.js`
- **RAG-API-001**: RAG问答功能 → `unit/test-chat-store.js`
- **KNOW-API-001~004**: 知识库管理 → `unit/test-knowledge-store.js`

### Sprint 3：应用功能层 ✅
- **FRONT-INT-001**: 搜索流程集成测试 → `integration/test-search-flow.js`
- **FRONT-INT-002**: 问答流程集成测试 → `integration/test-chat-flow.js`
- **FRONT-INT-003**: 知识库管理流程集成测试 → `integration/test-knowledge-flow.js`
- **FRONT-INT-004**: 爬虫管理流程集成测试 → `integration/test-crawler-flow.js`
- **FRONT-INT-005**: 数据分析流程集成测试 → `integration/test-analytics-flow.js`

### Sprint 4：质量保证与交付 ✅
- **PERF-002~003**: 前端性能测试 → `performance/test-frontend-performance.js`
- **SEC-002, SEC-003, SEC-005**: 前端安全测试 → `security/test-frontend-security.js`
- **E2E-REAL-001**: 真正的端到端测试 → `e2e/test-complete-flow.spec.js` (需要Playwright)

**说明**: Sprint 4 的系统集成测试（INT-001~005）属于后端测试，不在前端测试范围内。

## 📁 测试目录结构

```
Frontend/tests/
├── unit/                                    # 单元测试 (7个)
│   ├── test-environment.js                 # 环境验证测试
│   ├── test-vue-framework.js               # Vue框架初始化测试
│   ├── test-router-config.js               # 路由配置测试
│   ├── test-auth-store.js                  # 认证Store测试
│   ├── test-search-store.js                # 搜索Store测试
│   ├── test-chat-store.js                  # 聊天Store测试
│   └── test-knowledge-store.js             # 知识库Store测试
├── integration/                             # 集成测试 (6个)
│   ├── test-auth-flow.js                   # 认证流程集成测试 (Sprint 1)
│   ├── test-search-flow.js                 # 搜索流程集成测试 (Sprint 3)
│   ├── test-chat-flow.js                   # 问答流程集成测试 (Sprint 3)
│   ├── test-knowledge-flow.js              # 知识库管理流程集成测试 (Sprint 3)
│   ├── test-crawler-flow.js                # 爬虫管理流程集成测试 (Sprint 3)
│   └── test-analytics-flow.js              # 数据分析流程集成测试 (Sprint 3)
├── e2e/                                    # 端到端测试 (1个)
│   └── test-complete-flow.spec.js          # 真正的E2E测试（需要Playwright）
├── performance/                             # 性能测试 (1个)
│   └── test-frontend-performance.js        # 前端性能测试
├── security/                                # 安全测试 (1个)
│   └── test-frontend-security.js           # 前端安全测试
├── setup.js                                # 测试环境设置
└── README.md                               # 测试文档
```

## 🧪 测试类型说明

### 单元测试 (Unit Tests)
- **位置**: `tests/unit/`
- **命名规范**: `test-<service_name>.js`
- **范围**: 测试单个函数、组件、Store
- **目标**: 验证单个功能模块的正确性
- **特点**: 使用Mock隔离外部依赖，快速执行
- **运行**: `npm run test:unit`

#### 单元测试套件

##### Store测试
- **test-auth-store.js**: 认证Store单元测试
  - 用户注册、登录、登出
  - Token管理和刷新
  - 密码重置和邮箱验证
  - 主题切换
  - 错误处理

- **test-search-store.js**: 搜索Store单元测试
  - 语义搜索功能
  - 搜索建议
  - 搜索历史管理
  - 搜索结果管理
  - 搜索过滤和排序

- **test-chat-store.js**: 聊天Store单元测试
  - RAG问答功能
  - 聊天历史管理
  - 检索上下文管理
  - 聊天会话管理
  - 消息导出功能

- **test-knowledge-store.js**: 知识库Store单元测试
  - 知识库列表管理
  - CRUD操作
  - 知识库过滤和搜索
  - 知识库排序
  - 批量操作
  - 统计信息

##### 基础设施测试
- **test-vue-framework.js**: Vue框架初始化测试
  - Vue应用实例创建
  - Pinia插件安装
  - 应用挂载
  - 组件注册

- **test-router-config.js**: 路由配置测试
  - 路由实例创建
  - 路由规则验证
  - 路由元信息配置
  - 路由解析

### 集成测试 (Integration Tests)
- **位置**: `tests/integration/`
- **命名规范**: `test-<feature>-flow.js`
- **范围**: 测试组件与Store的集成
- **目标**: 验证模块间的交互功能
- **特点**: 使用Mock API，测试组件与Store集成
- **运行**: `npm run test:integration:all`

#### 集成测试套件
- **test-auth-flow.js**: 认证流程集成测试
  - 完整登录流程
  - 完整注册流程
  - 表单验证
  - 错误处理

- **test-search-flow.js**: 搜索流程集成测试
  - 搜索框 + Store + Mock API集成
  - 搜索建议流程
  - 搜索历史保存
  - 错误处理

- **test-chat-flow.js**: 问答流程集成测试
  - 聊天界面 + Store + Mock API集成
  - 连续对话流程
  - 检索上下文显示
  - 错误处理

- **test-knowledge-flow.js**: 知识库管理流程集成测试
  - 知识库界面 + Store + Mock API集成
  - CRUD操作流程
  - 过滤和搜索
  - 错误处理

- **test-crawler-flow.js**: 爬虫管理流程集成测试
  - 爬虫界面 + Mock API集成
  - 任务创建和控制
  - 任务详情查看
  - 错误处理

- **test-analytics-flow.js**: 数据分析流程集成测试（考核必需）
  - 分析界面 + Mock API集成
  - Top10关键词展示
  - 数据聚类展示
  - 数据导出功能

### 端到端测试 (End-to-End Tests)
- **位置**: `tests/e2e/`
- **工具**: Playwright（真实浏览器环境）
- **特点**: 不使用Mock，测试真实前端+后端+数据库
- **运行**: `npx playwright test`

#### 测试套件
- **test-complete-flow.spec.js**: 完整用户流程E2E测试
  - 用户注册 → 登录 → 搜索完整流程
  - 登录 → 知识库管理流程
  - 登录 → 数据分析页面展示

#### 使用说明
E2E测试为**可选项**，需要真实环境：

**前置条件**：
```bash
# 1. 安装 Playwright（在 Frontend 目录）
cd Frontend
npm install -D @playwright/test
npx playwright install
```

**运行测试**：
```bash
# 1. 启动后端服务（终端1）
cd Backend
python app.py
# 后端运行在 http://localhost:5000

# 2. 启动前端服务（终端2）
cd Frontend
npm run dev
# 前端运行在 http://localhost:3000

# 3. 检查服务状态（可选）
cd Frontend
npm run test:e2e:check              # 检查前后端服务是否运行

# 4. 准备测试数据（首次运行或需要时）
npm run test:e2e:setup              # 创建测试账号

# 5. 运行E2E测试（终端3）
cd Frontend
npm run test:e2e                    # 运行所有E2E测试
npm run test:e2e:ui                 # UI模式（推荐）
npm run test:e2e:headed             # 有头模式（可见浏览器）
npm run test:e2e:report             # 查看测试报告
```

**注意**: 
- E2E测试必须在 `Frontend/` 目录下运行
- 必须确保后端（5000端口）和前端（3000端口）服务都在运行
- 测试使用真实的数据库和API，不使用Mock
- 日常开发使用单元测试和集成测试即可
- E2E测试适合关键发布前的完整验证

## 🚀 运行测试

### 安装测试依赖
```bash
cd Frontend
npm install
```

### 运行所有测试
```bash
# 运行所有测试
npm run test:all

# 运行所有单元测试
npm run test:unit:all

# 运行所有集成测试
npm run test:integration:all

# 运行所有端到端测试
npm run test:e2e:all

# 运行所有性能测试
npm run test:performance:all

# 运行所有安全测试
npm run test:security:all
```

### 运行单个测试文件（推荐）
```bash
# 单元测试 - 必须指定完整路径
npm run test:unit tests/unit/test-environment.js
npm run test:unit tests/unit/test-auth-store.js
npm run test:unit tests/unit/test-search-store.js

# 集成测试 - 必须指定完整路径
npm run test:integration tests/integration/test-auth-flow.js
npm run test:integration tests/integration/test-search-flow.js

# E2E测试 - 使用 Playwright（需在 Frontend/ 目录）
cd Frontend
npx playwright test tests/e2e/test-complete-flow.spec.js
npx playwright test --ui  # UI模式运行

# 性能测试
npm run test:performance tests/performance/test-frontend-performance.js

# 安全测试
npm run test:security tests/security/test-frontend-security.js
```

### 运行多个测试文件
```bash
# 同时运行多个单元测试
npm run test:unit tests/unit/test-auth-store.js tests/unit/test-search-store.js

# 运行所有E2E测试（需在 Frontend/ 目录）
cd Frontend && npx playwright test
```

### 其他测试模式
```bash
# 监听模式（自动重新运行）
npm run test:watch

# 覆盖率测试
npm run test:coverage
```

### 按测试计划Sprint运行
```bash
# Sprint 0: 基础环境测试（3个）
npm run test:unit tests/unit/test-environment.js
npm run test:unit tests/unit/test-vue-framework.js
npm run test:unit tests/unit/test-router-config.js

# Sprint 1: 认证模块测试（2个）
npm run test:unit tests/unit/test-auth-store.js
npm run test:integration tests/integration/test-auth-flow.js

# Sprint 2: 数据与AI服务层测试（3个）
npm run test:unit tests/unit/test-search-store.js
npm run test:unit tests/unit/test-chat-store.js
npm run test:unit tests/unit/test-knowledge-store.js

# Sprint 3: 应用功能层测试（5个）
npm run test:integration tests/integration/test-search-flow.js
npm run test:integration tests/integration/test-chat-flow.js
npm run test:integration tests/integration/test-knowledge-flow.js
npm run test:integration tests/integration/test-crawler-flow.js
npm run test:integration tests/integration/test-analytics-flow.js

# Sprint 4: 质量保证测试（2个）
npm run test:performance tests/performance/test-frontend-performance.js
npm run test:security tests/security/test-frontend-security.js
```

## 📊 测试覆盖率

### 覆盖率目标
- **单元测试**: > 80%
- **集成测试**: > 60%
- **E2E测试**: 核心流程全覆盖

### 查看覆盖率报告
```bash
npm run test:coverage
# 报告生成在 coverage/ 目录
# 在浏览器中打开 coverage/index.html 查看详细报告
```

### 当前覆盖率统计
| 测试类型 | 测试文件数 | 覆盖范围 | 状态 |
|---------|----------|---------|------|
| 单元测试 | 7个 | Store、基础设施、环境 | ✅ |
| 集成测试 | 6个 | 认证、搜索、问答、知识库、爬虫、分析 | ✅ |
| E2E测试 | 1个 | 完整用户流程（Playwright，可选） | 📝 |
| 性能测试 | 1个 | 搜索、问答、页面加载 | ✅ |
| 安全测试 | 1个 | XSS、CSRF、JWT | ✅ |
| **总计** | **16个** | **完整覆盖Sprint 0-4** | **✅** |

**测试分布**：
- Sprint 0: 3个单元测试（环境、框架、路由）
- Sprint 1: 1个单元测试 + 1个集成测试（认证）
- Sprint 2: 3个单元测试（搜索、问答、知识库 Store）
- Sprint 3: 5个集成测试（搜索、问答、知识库、爬虫、分析流程）
- Sprint 4: 1个性能测试 + 1个安全测试 + 1个E2E测试（可选）

## 🔧 测试配置

### Vitest 配置
```javascript
// vitest.config.js
export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.js']
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  }
})
```

### 测试环境设置
```javascript
// tests/setup.js
import { vi } from 'vitest'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
global.localStorage = localStorageMock
```

## 📝 测试最佳实践

### 1. 测试文件命名
- 单元测试: `test-<service_name>.js`
- 集成测试: `test-<feature>-flow.js`
- E2E测试: `test-<feature>.spec.js` (Playwright)

### 2. 测试套件结构
```javascript
/**
 * 测试文件头部注释
 * 测试用例ID: XXX-001
 * 对应测试计划: Sprint X - XXX
 * 测试描述: XXX
 */
describe('测试套件名称', () => {
  beforeEach(() => {
    // 准备测试环境
  })

  describe('功能模块1', () => {
    it('应该满足某个条件', () => {
      // Arrange - 准备测试数据
      // Act - 执行被测试的功能
      // Assert - 验证结果
    })
  })
})
```

### 3. Mock使用原则

| 测试类型 | Mock策略 | 环境 |
|---------|---------|------|
| 单元测试 | Mock所有外部依赖 | Vitest + jsdom |
| 集成测试 | Mock API，保留Store | Vitest + jsdom |
| E2E测试 | 不Mock，真实服务 | Playwright + 真实浏览器 |

```javascript
// 单元/集成测试 Mock 示例
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  register: vi.fn()
}))
```

### 4. 组件测试
```javascript
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'

const wrapper = mount(Component, {
  global: {
    plugins: [createPinia()]
  },
  props: {
    // 组件props
  }
})

// 测试组件行为
await wrapper.find('button').trigger('click')
expect(wrapper.emitted('submit')).toBeTruthy()
```

### 5. 异步测试
```javascript
it('应该处理异步操作', async () => {
  await store.fetchData()
  expect(store.data).toBeDefined()
  
  // 等待DOM更新
  await wrapper.vm.$nextTick()
  
  // 等待特定时间
  await new Promise(resolve => setTimeout(resolve, 1000))
})
```

### 6. 数据驱动测试
```javascript
describe.each([
  { input: 'test1', expected: 'result1' },
  { input: 'test2', expected: 'result2' },
  { input: 'test3', expected: 'result3' }
])('测试不同输入', ({ input, expected }) => {
  it(`输入${input}应该返回${expected}`, () => {
    const result = processInput(input)
    expect(result).toBe(expected)
  })
})
```

## 🐛 常见问题

### 1. 模块导入问题
**问题**: 找不到模块 `@/xxx`
**解决**: 检查 `vitest.config.js` 中的路径别名配置

### 2. Mock问题
**问题**: Mock函数没有被调用
**解决**: 
- 确保Mock在测试之前设置
- 使用 `vi.clearAllMocks()` 清理Mock状态

### 3. 异步测试超时
**问题**: 测试超时失败
**解决**:
- 使用 `await` 等待异步操作
- 增加测试超时时间
- 检查是否有未完成的Promise

### 4. 组件挂载问题
**问题**: 组件挂载失败
**解决**:
- 确保提供必要的依赖（Pinia、Router等）
- 检查组件的props和slots
- 查看控制台错误信息

### 5. E2E测试失败
**问题**: E2E测试无法连接后端  
**解决**: 确保后端（localhost:5000）和前端（localhost:5173）服务都在运行

## 📈 持续改进

### 测试质量指标
- ✅ 测试覆盖率 > 80%
- ✅ 测试执行时间 < 30秒
- ✅ 测试稳定性 > 95%
- ✅ 所有考核要求覆盖

### 测试维护
1. **定期更新**: 功能变更时同步更新测试
2. **代码审查**: 测试代码也需要审查
3. **监控结果**: 持续关注测试执行结果
4. **重构优化**: 定期重构测试代码，提高可维护性

## 🔄 CI/CD集成

### GitHub Actions 示例
```yaml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: '18'
      - run: npm install
      - run: npm run test:unit
      - run: npm run test:integration
      - run: npm run test:coverage
```

## 📚 相关文档

- **测试计划文档**: [测试计划文档_v3.md](../../Docs/测试计划文档_v3.md)
- **技术架构文档**: [技术架构文档.md](../../Docs/技术架构文档.md)
- **概要设计文档**: [概要设计文档_v2.md](../../Docs/概要设计文档_v2.md)
- **后端测试文档**: [Backend/tests/README.md](../../Backend/tests/README.md)

## 📞 支持

如有测试相关问题，请：
1. 查看本文档的常见问题部分
2. 查看测试计划文档
3. 查看Vitest官方文档
4. 联系项目维护者

---

**文档版本**: v3.4（测试优化版）  
**创建时间**: 2025-01-06  
**最后更新**: 2025-01-09  
**测试状态**: ✅ 所有测试套件已完成，测试分类准确  
**测试统计**: 16个测试文件，覆盖Sprint 0-4所有测试类型  
**测试分布**: 7个单元测试 + 6个集成测试 + 1个E2E测试 + 1个性能测试 + 1个安全测试  
**重要更新**:
- 重新分类测试：将伪E2E测试正确分类为前端集成测试
- 删除7个不符合测试计划的测试套件（包括 test-system-integration.js）
- 系统集成测试（INT-001~005）属于后端测试，已从前端测试中移除
- 前端集成测试精简为6个，直接测试 API 调用而非组件交互
- 添加真正的E2E测试说明（Playwright）
- 明确测试分层：单元（Mock所有）→ 集成（Mock API）→ E2E（不Mock）
