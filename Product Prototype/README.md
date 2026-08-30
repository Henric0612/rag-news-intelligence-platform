# RAG News Intelligence Platform 产品原型

## 📋 概述

基于Vue.js构建的智能新闻检索与问答系统原型，展示核心用户界面和交互流程，验证产品设计理念。

**核心特色**
- 智能新闻检索 - 基于RAG技术的语义检索
- AI智能问答 - 对话式问答与流式输出
- 个人知识库 - 文档上传与管理
- 现代化界面 - 暗色主题，响应式设计

---

## 🗂️ 页面结构

| 页面 | 功能 | 设计要点 |
|------|------|----------|
| `index.html` | 用户认证 | 登录/注册切换、表单验证、游客模式 |
| `home.html` | 首页搜索 | 搜索框、热门标签、快捷入口 |
| `results.html` | 搜索结果 | 时间筛选、相关度评分、结果列表 |
| `qa.html` | RAG问答 | 对话界面、流式输出、答案溯源、置信度展示 |
| `library.html` | 知识库管理 | 文档列表、批量操作、状态展示 |
| `upload.html` | 文档上传 | 多文件选择、进度可视化 |

**用户流程**
```
登录 → 首页搜索 → 查看结果 → AI问答（查看溯源）
        ↓
      文档上传 → 知识库管理 → 基于文档问答
```

---

## 🎨 设计系统

### 色彩规范
```css
--brand: #5b8eff;    /* 主品牌色 */
--accent: #22d3ee;   /* 强调色 */
--bg: #0f1115;       /* 背景 */
--text: #e7eaf0;     /* 主文本 */
--muted: #a8b0c0;    /* 次要文本 */
```

### 组件规范
- **按钮**: Primary（品牌色）、Ghost（透明）、普通（卡片色）
- **卡片**: 渐变背景 + 圆角边框 + 阴影
- **表单**: 暗色输入框 + 聚焦高亮
- **对话气泡**: 用户（右对齐）vs AI（左对齐）

### 响应式断点
- **桌面**: ≥1200px - 完整功能
- **平板**: 768-1199px - 适配布局
- **移动**: <768px - 简化导航

---

## 🔧 技术实现

**技术栈**
- Vue 3 (CDN) + Composition API
- 原生CSS + Grid/Flexbox
- ES6 Modules

**关键优化**
- `v-cloak` 防止模板闪烁
- 加载动画提升体验
- 流式输出模拟AI回答

**目录结构**
```
产品原型/
├── pages/          # 6个核心页面
├── components/     # navbar.js, footer.js
├── assets/         # styles.css
└── README.md
```

---

## 🚀 快速启动

**⚠️ 必须使用HTTP服务器运行（ES6 Modules限制）**

```bash
# 方法1：Python
cd 产品原型
python -m http.server 8080
# 访问 http://localhost:8080/pages/index.html

# 方法2：Node.js
npx serve -p 8080

# 方法3：VSCode Live Server插件
# 右键HTML → Open with Live Server
```

**页面访问**
- 登录: `/pages/index.html`
- 首页: `/pages/home.html`
- 问答: `/pages/qa.html`
- 知识库: `/pages/library.html`

---

## 🎯 设计验证点

### 功能验证
- ✅ 语义检索界面设计
- ✅ RAG问答交互流程
- ✅ 知识库管理操作
- ✅ 答案溯源与置信度展示

### 体验验证
- ✅ 3次点击内到达核心功能
- ✅ 清晰的信息架构
- ✅ 流畅的加载体验
- ✅ 多设备响应式适配

---

## 📝 产品需求对应

| 需求模块 | 原型验证 |
|---------|---------|
| 用户认证系统 | `index.html` 表单与状态管理 |
| 智能检索引擎 | `home.html` + `results.html` 搜索与筛选 |
| RAG问答系统 | `qa.html` 对话、流式输出、溯源 |
| 知识库管理 | `library.html` + `upload.html` 文档操作 |

---

*本原型为后续全栈开发提供UI/UX指导基准*
