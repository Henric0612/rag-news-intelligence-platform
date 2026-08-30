import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

// 懒加载组件工厂
const lazyLoad = (componentName) => {
  return () => import(`@/views/${componentName}.vue`)
}

const lazyLoadComponent = (componentPath) => {
  return () => import(`@/components/${componentPath}.vue`)
}

// 路由配置
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: lazyLoad('Login'),
    meta: { 
      title: '登录',
      requiresAuth: false,
      hideInMenu: true
    }
  },
  {
    path: '/password-reset',
    name: 'PasswordReset',
    component: lazyLoad('PasswordReset'),
    meta: { 
      title: '密码重置',
      requiresAuth: false,
      hideInMenu: true
    }
  },
  {
    path: '/verify-email',
    name: 'EmailVerification',
    component: lazyLoad('EmailVerification'),
    meta: { 
      title: '邮箱验证',
      requiresAuth: false,
      hideInMenu: true
    }
  },
  {
    path: '/',
    name: 'Layout',
    component: lazyLoadComponent('Layout'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: lazyLoad('Dashboard'),
        meta: { 
          title: '仪表板',
          icon: 'House'
        }
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: lazyLoad('Knowledge'),
        meta: { 
          title: '知识库',
          icon: 'Document'
        }
      },
      {
        path: 'search',
        name: 'Search',
        component: lazyLoad('Search'),
        meta: { 
          title: '智能搜索',
          icon: 'Search'
        }
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: lazyLoad('Analytics'),
        meta: { 
          title: '数据分析',
          icon: 'TrendCharts'
        }
      },
      {
        path: 'crawler',
        name: 'Crawler',
        component: lazyLoad('Crawler'),
        meta: { 
          title: '数据采集',
          icon: 'Download'
        }
      },
      {
        path: 'health',
        name: 'Health',
        component: lazyLoad('Health'),
        meta: { 
          title: '系统健康',
          icon: 'Monitor'
        }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: lazyLoad('NotFound'),
    meta: { 
      title: '页面不存在',
      hideInMenu: true
    }
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - RAG News Intelligence Platform` : 'RAG News Intelligence Platform'
  
  // 确保认证状态已初始化
  if (!authStore.initialized) {
    await authStore.initAuthState()
  }
  
  // 检查是否需要认证
  if (to.meta.requiresAuth !== false) {
    // 验证 token 有效性
    try {
      await authStore.checkAuth()
    } catch (error) {
      console.error('认证检查失败:', error)
      authStore.clearAuthState()
      
      // ✅ 检查是否应该静默处理
      const shouldSilent = authStore.shouldSilentAuth()
      if (shouldSilent) {
        console.log('长时间未使用，静默重定向到登录页')
        next('/login')
        return
      } else {
        // 主动登录失败，显示提示
        ElMessage.warning('请先登录')
        next('/login')
        return
      }
    }
    
    // 再次检查登录状态（checkAuth可能会清除认证）
    if (!authStore.isLoggedIn) {
      const shouldSilent = authStore.shouldSilentAuth()
      if (shouldSilent) {
        console.log('长时间未使用，静默重定向到登录页')
        next('/login')
        return
      } else {
        ElMessage.warning('请先登录')
        next('/login')
        return
      }
    }
  }
  
  // 如果已登录用户访问登录页，重定向到首页
  if (to.path === '/login' && authStore.isLoggedIn) {
    next('/')
    return
  }
  
  next()
})

// 全局后置钩子
router.afterEach((to, from) => {
  // 可以在这里添加页面访问统计等逻辑
  console.log(`路由跳转: ${from.path} -> ${to.path}`)
})

export default router
