import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import App from './App.vue'
import router from './router'
import './assets/styles/global.css'
import { useAuthStore } from './stores/auth'
import { setupVueErrorHandler, setupGlobalErrorHandler } from './utils/errorHandler'
import activityTracker from './utils/activityTracker'

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.use(pinia)
app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
})

// 设置全局错误处理
setupVueErrorHandler(app)
setupGlobalErrorHandler()

// 初始化认证状态
const authStore = useAuthStore()
authStore.initAuthState().then(() => {
  // ✅ 初始化用户活动追踪
  activityTracker.init()
  app.mount('#app')
}).catch(error => {
  console.error('初始化认证状态失败:', error)
  app.mount('#app')
})
