import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'
import './styles/index.scss'

const app = createApp(App)

// 状态管理
const pinia = createPinia()
app.use(pinia)

// 路由
app.use(router)

// Element Plus
app.use(ElementPlus, {
  locale: zhCn,
  size: 'default'
})

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 全局属性
app.config.globalProperties.$ELEMENT = {
  size: 'default'
}

// 开发环境调试
if (import.meta.env.DEV) {
  app.config.globalProperties.$log = console.log
  window.app = app
}

// 全局错误处理
app.config.errorHandler = (err, instance, info) => {
  console.error('Global error:', err)
  console.error('Error info:', info)
  
  // 这里可以添加错误上报逻辑
  if (import.meta.env.PROD) {
    // 生产环境错误上报
    // reportError(err, info)
  }
}

app.mount('#app')

console.log('🚀 AI管理系统前端启动成功')
console.log('📊 当前环境:', import.meta.env.MODE)
console.log('🔗 API地址:', import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')