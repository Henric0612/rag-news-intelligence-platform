<template>
  <div class="layout">
    <AppHeader />
    <div class="layout-content">
      <AppSidebar />
      <main class="main-content">
        <PageContainer>
          <router-view />
        </PageContainer>
      </main>
    </div>
  </div>
</template>

<script setup>
import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'
import PageContainer from './PageContainer.vue'
</script>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.layout-content {
  flex: 1;
  display: flex;
  min-height: calc(100vh - 60px);
}

.main-content {
  flex: 1;
  background-color: var(--bg-secondary);
  overflow-y: auto;
}

@media (max-width: 768px) {
  .layout-content {
    flex-direction: column;
  }
  
  .main-content {
    min-height: calc(100vh - 120px);
  }
}
</style>
