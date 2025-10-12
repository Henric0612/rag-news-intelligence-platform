<template>
  <aside class="tech-sidebar" :class="{ collapsed: collapsed }">
    <div class="sidebar-content">
      <nav class="nav-menu">
        <el-menu
          :default-active="activeMenu"
          :collapse="collapsed"
          :unique-opened="true"
          router
          class="nav-menu-list"
        >
          <el-menu-item 
            v-for="route in menuRoutes" 
            :key="route.name"
            :index="route.path"
            :route="route"
          >
            <el-icon><component :is="route.meta.icon" /></el-icon>
            <template #title>{{ route.meta.title }}</template>
          </el-menu-item>
        </el-menu>
      </nav>
      
      <div class="sidebar-footer">
        <el-button 
          :icon="collapsed ? Expand : Fold" 
          circle 
          size="small"
          @click="toggleCollapse"
          class="collapse-btn"
        />
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Expand, Fold } from '@element-plus/icons-vue'

const route = useRoute()
const collapsed = ref(false)

// 菜单路由配置
const menuRoutes = [
  {
    path: '/dashboard',
    name: 'Dashboard',
    meta: { title: '仪表板', icon: 'House' }
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    meta: { title: '知识库', icon: 'Document' }
  },
  {
    path: '/search',
    name: 'Search',
    meta: { title: '智能搜索', icon: 'Search' }
  },
  {
    path: '/analytics',
    name: 'Analytics',
    meta: { title: '数据分析', icon: 'TrendCharts' }
  },
  {
    path: '/crawler',
    name: 'Crawler',
    meta: { title: '数据采集', icon: 'Download' }
  },
  {
    path: '/health',
    name: 'Health',
    meta: { title: '系统健康', icon: 'Monitor' }
  }
]

const activeMenu = computed(() => {
  return route.path
})

const toggleCollapse = () => {
  collapsed.value = !collapsed.value
  localStorage.setItem('sidebar-collapsed', collapsed.value.toString())
}

// 初始化侧边栏状态
const initSidebar = () => {
  const saved = localStorage.getItem('sidebar-collapsed')
  if (saved !== null) {
    collapsed.value = saved === 'true'
  }
}

// 组件挂载时初始化
initSidebar()
</script>

<style scoped>
.tech-sidebar {
  width: 240px;
  background: var(--bg-color);
  border-right: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  transition: width var(--transition-normal);
  overflow: hidden;
}

.tech-sidebar.collapsed {
  width: 64px;
}

.sidebar-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.nav-menu {
  flex: 1;
  overflow-y: auto;
}

.nav-menu-list {
  border: none;
  background: transparent;
}

.nav-menu-list :deep(.el-menu-item) {
  height: 48px;
  line-height: 48px;
  margin: 4px 8px;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.nav-menu-list :deep(.el-menu-item:hover) {
  background-color: var(--bg-secondary);
  color: var(--primary-color);
}

.nav-menu-list :deep(.el-menu-item.is-active) {
  background-color: var(--primary-bg);
  color: var(--primary-color);
  font-weight: var(--font-medium);
}

.nav-menu-list :deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background-color: var(--primary-color);
  border-radius: 0 2px 2px 0;
}

.sidebar-footer {
  padding: var(--space-md);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: center;
}

.collapse-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.collapse-btn:hover {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: var(--white);
}

@media (max-width: 768px) {
  .tech-sidebar {
    position: fixed;
    top: 60px;
    left: 0;
    height: calc(100vh - 60px);
    z-index: var(--z-fixed);
    transform: translateX(-100%);
    transition: transform var(--transition-normal);
  }
  
  .tech-sidebar.collapsed {
    transform: translateX(0);
  }
}
</style>
