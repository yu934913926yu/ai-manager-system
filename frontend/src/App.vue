<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'

const userStore = useUserStore()
const appStore = useAppStore()

onMounted(async () => {
  // 初始化应用
  try {
    // 检查本地存储的token
    await userStore.checkAuth()
    
    // 初始化应用配置
    appStore.initApp()
    
    console.log('✅ 应用初始化完成')
  } catch (error) {
    console.error('❌ 应用初始化失败:', error)
  }
})
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  height: 100vh;
  width: 100vw;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  overflow: hidden;
}

/* 全局滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Element Plus 自定义样式 */
.el-message-box {
  border-radius: 8px;
}

.el-dialog {
  border-radius: 8px;
}

.el-card {
  border-radius: 8px;
}
</style>