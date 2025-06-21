<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <img src="/logo.png" alt="Logo" class="logo">
        <h1>AI管理系统</h1>
        <p>智能化项目管理平台</p>
      </div>
      
      <el-form 
        ref="loginFormRef"
        :model="loginForm" 
        :rules="loginRules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            size="large"
            clearable
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            size="large"
            show-password
            clearable
          />
        </el-form-item>
        
        <el-form-item>
          <el-checkbox v-model="loginForm.remember">记住我</el-checkbox>
          <el-link type="primary" :underline="false" class="forgot-password">
            忘记密码？
          </el-link>
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleLogin"
            class="login-button"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
        
        <div class="login-tips">
          <p>演示账号：admin / admin123</p>
        </div>
      </el-form>
      
      <el-divider>或</el-divider>
      
      <div class="other-login">
        <el-button 
          size="large" 
          @click="handleWechatLogin"
          class="wechat-button"
        >
          <el-icon><ChatDotRound /></el-icon>
          企业微信登录
        </el-button>
      </div>
    </div>
    
    <div class="login-footer">
      <p>&copy; 2024 AI管理系统 - Powered by Claude</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { User, Lock, ChatDotRound } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/utils/api'
import { tokenStorage } from '@/utils/auth'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 表单引用
const loginFormRef = ref()

// 加载状态
const loading = ref(false)

// 登录表单
const loginForm = reactive({
  username: '',
  password: '',
  remember: false
})

// 表单验证规则
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' }
  ]
}

// 处理登录
const handleLogin = async () => {
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  
  try {
    const response = await authApi.login({
      username: loginForm.username,
      password: loginForm.password
    })
    
    if (response.success) {
      // 保存token和用户信息
      tokenStorage.setToken(response.data.access_token)
      tokenStorage.setRefreshToken(response.data.refresh_token)
      userStore.setUser(response.data.user)
      
      // 记住我功能
      if (loginForm.remember) {
        localStorage.setItem('remembered_username', loginForm.username)
      } else {
        localStorage.removeItem('remembered_username')
      }
      
      ElMessage.success('登录成功')
      
      // 显示欢迎通知
      ElNotification({
        title: '欢迎回来',
        message: `${response.data.user.full_name || response.data.user.username}，祝您工作愉快！`,
        type: 'success',
        duration: 3000
      })
      
      // 跳转到目标页面
      const redirect = route.query.redirect || '/dashboard'
      router.push(redirect)
      
    } else {
      ElMessage.error(response.message || '登录失败')
    }
    
  } catch (error) {
    console.error('登录错误:', error)
    ElMessage.error(error.response?.data?.detail || '登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

// 企业微信登录
const handleWechatLogin = () => {
  ElMessage.info('企业微信登录功能开发中...')
  
  // TODO: 实现企业微信扫码登录
  // 1. 获取企业微信登录二维码
  // 2. 轮询登录状态
  // 3. 登录成功后跳转
}

// 页面加载时
onMounted(() => {
  // 自动填充记住的用户名
  const rememberedUsername = localStorage.getItem('remembered_username')
  if (rememberedUsername) {
    loginForm.username = rememberedUsername
    loginForm.remember = true
  }
  
  // 检查是否已登录
  if (userStore.isLoggedIn) {
    router.push('/dashboard')
  }
})
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  padding: 40px;
  animation: fadeInUp 0.6s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo {
  width: 80px;
  height: 80px;
  margin-bottom: 20px;
}

.login-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 10px;
}

.login-header p {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.login-form {
  margin-bottom: 20px;
}

.login-form :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}

.forgot-password {
  float: right;
}

.login-button {
  width: 100%;
  font-size: 16px;
  letter-spacing: 2px;
}

.login-tips {
  text-align: center;
  margin-top: 20px;
}

.login-tips p {
  color: #909399;
  font-size: 12px;
  margin: 0;
}

.other-login {
  text-align: center;
}

.wechat-button {
  width: 100%;
  background-color: #07C160;
  color: white;
  border: none;
}

.wechat-button:hover {
  background-color: #06a550;
}

.login-footer {
  margin-top: 40px;
  text-align: center;
  color: white;
  font-size: 12px;
}

@media (max-width: 480px) {
  .login-card {
    padding: 30px 20px;
  }
  
  .login-header h1 {
    font-size: 24px;
  }
}
</style>