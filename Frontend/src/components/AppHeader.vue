<template>
  <header class="tech-header">
    <div class="header-content">
      <div class="header-left">
        <h1 class="logo">
          <el-icon class="logo-icon"><DataAnalysis /></el-icon>
          XU News AI RAG
        </h1>
      </div>
      
      <div class="header-right">
        <DarkModeToggle />
        
        <el-dropdown @command="handleCommand" v-if="authStore.isLoggedIn">
          <div class="user-info">
            <el-avatar :size="32" :src="userAvatar">
              <el-icon><User /></el-icon>
            </el-avatar>
            <span class="username">{{ authStore.userInfo?.username || '用户' }}</span>
            <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                个人资料
              </el-dropdown-item>
              <el-dropdown-item command="settings">
                <el-icon><Setting /></el-icon>
                设置
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import DarkModeToggle from './DarkModeToggle.vue'

const router = useRouter()
const authStore = useAuthStore()

const userAvatar = computed(() => {
  // 这里可以根据用户信息返回头像URL
  return null
})

const handleCommand = async (command) => {
  switch (command) {
    case 'profile':
      ElMessage.info('个人资料功能开发中')
      break
    case 'settings':
      ElMessage.info('设置功能开发中')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm(
          '确定要退出登录吗？',
          '确认退出',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        await authStore.logout()
        router.push('/login')
      } catch (error) {
        // 用户取消
      }
      break
  }
}
</script>

<style scoped>
.tech-header {
  height: 60px;
  background: var(--bg-color);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
}

.header-content {
  height: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin: 0;
}

.logo-icon {
  color: var(--primary-color);
  font-size: 24px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.user-info:hover {
  background-color: var(--bg-secondary);
}

.username {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.dropdown-icon {
  font-size: 12px;
  color: var(--text-tertiary);
}

@media (max-width: 768px) {
  .header-content {
    padding: 0 var(--space-md);
  }
  
  .logo {
    font-size: var(--text-lg);
  }
  
  .username {
    display: none;
  }
}
</style>
