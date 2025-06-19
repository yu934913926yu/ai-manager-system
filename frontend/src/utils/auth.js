#!/usr/bin/env javascript
/**
 * 前端认证工具模块
 * 处理JWT token存储、验证和用户权限检查
 * 支持多角色权限控制：admin, designer, finance
 */

// 🔑 Token存储相关常量
const TOKEN_KEY = 'ai_manager_token'
const REFRESH_TOKEN_KEY = 'ai_manager_refresh_token'
const USER_INFO_KEY = 'ai_manager_user_info'
const TOKEN_EXPIRE_KEY = 'ai_manager_token_expire'

/**
 * 🏪 Token存储管理
 */
export const tokenStorage = {
  // 获取访问Token
  getToken() {
    return localStorage.getItem(TOKEN_KEY)
  },

  // 设置访问Token
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token)
  },

  // 获取刷新Token
  getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  },

  // 设置刷新Token
  setRefreshToken(refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  },

  // 获取Token过期时间
  getTokenExpire() {
    const expire = localStorage.getItem(TOKEN_EXPIRE_KEY)
    return expire ? parseInt(expire) : null
  },

  // 设置Token过期时间
  setTokenExpire(timestamp) {
    localStorage.setItem(TOKEN_EXPIRE_KEY, timestamp.toString())
  },

  // 清除所有Token
  clearTokens() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(TOKEN_EXPIRE_KEY)
    localStorage.removeItem(USER_INFO_KEY)
  },

  // 检查Token是否存在
  hasToken() {
    return !!this.getToken()
  }
}

/**
 * 👤 用户信息管理
 */
export const userStorage = {
  // 获取用户信息
  getUserInfo() {
    const userStr = localStorage.getItem(USER_INFO_KEY)
    return userStr ? JSON.parse(userStr) : null
  },

  // 设置用户信息
  setUserInfo(userInfo) {
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo))
  },

  // 清除用户信息
  clearUserInfo() {
    localStorage.removeItem(USER_INFO_KEY)
  },

  // 获取用户角色
  getUserRole() {
    const userInfo = this.getUserInfo()
    return userInfo?.role || null
  },

  // 获取用户ID
  getUserId() {
    const userInfo = this.getUserInfo()
    return userInfo?.id || null
  },

  // 获取用户权限列表
  getUserPermissions() {
    const userInfo = this.getUserInfo()
    return userInfo?.permissions || []
  }
}

/**
 * 🕐 Token有效性检查
 */
export const tokenValidator = {
  // 检查Token是否过期
  isTokenExpired() {
    const expire = tokenStorage.getTokenExpire()
    if (!expire) return true
    
    const now = Math.floor(Date.now() / 1000)
    return now >= expire
  },

  // 检查Token是否即将过期 (30分钟内)
  isTokenExpiringSoon() {
    const expire = tokenStorage.getTokenExpire()
    if (!expire) return true
    
    const now = Math.floor(Date.now() / 1000)
    const thirtyMinutes = 30 * 60
    return (expire - now) <= thirtyMinutes
  },

  // 解析JWT Token payload
  parseJwtPayload(token) {
    try {
      const parts = token.split('.')
      if (parts.length !== 3) return null
      
      const payload = parts[1]
      const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
      return JSON.parse(decoded)
    } catch (error) {
      console.error('JWT解析失败:', error)
      return null
    }
  },

  // 验证Token格式和基本有效性
  validateTokenFormat(token) {
    if (!token || typeof token !== 'string') return false
    
    const parts = token.split('.')
    if (parts.length !== 3) return false
    
    const payload = this.parseJwtPayload(token)
    if (!payload) return false
    
    // 检查必要字段
    return !!(payload.user_id && payload.role && payload.exp)
  }
}

/**
 * 🔐 权限检查系统
 */
export const permissionChecker = {
  // 角色权限映射
  rolePermissions: {
    admin: [
      // 项目管理
      'project:read', 'project:create', 'project:update', 'project:delete',
      // 任务管理
      'task:read', 'task:create', 'task:update', 'task:delete',
      // 供应商管理
      'supplier:read', 'supplier:create', 'supplier:update', 'supplier:delete',
      // 用户管理
      'user:read', 'user:create', 'user:update', 'user:delete',
      // 财务管理
      'finance:read', 'finance:update',
      // 系统管理
      'system:config', 'report:view'
    ],
    designer: [
      // 项目管理 (部分权限)
      'project:read', 'project:update',
      // 任务管理
      'task:read', 'task:update',
      // 供应商管理 (只读)
      'supplier:read'
    ],
    finance: [
      // 项目管理 (只读)
      'project:read',
      // 财务管理
      'finance:read', 'finance:update',
      // 报告查看
      'report:view'
    ]
  },

  // 检查用户是否有指定权限
  hasPermission(permission) {
    const role = userStorage.getUserRole()
    if (!role) return false
    
    // admin拥有所有权限
    if (role === 'admin') return true
    
    const permissions = this.rolePermissions[role] || []
    return permissions.includes(permission)
  },

  // 检查用户是否有任一权限
  hasAnyPermission(permissions) {
    return permissions.some(permission => this.hasPermission(permission))
  },

  // 检查用户是否有所有权限
  hasAllPermissions(permissions) {
    return permissions.every(permission => this.hasPermission(permission))
  },

  // 检查用户角色
  hasRole(role) {
    const userRole = userStorage.getUserRole()
    return userRole === role
  },

  // 检查用户是否有任一角色
  hasAnyRole(roles) {
    const userRole = userStorage.getUserRole()
    return roles.includes(userRole)
  }
}

/**
 * 🔒 认证状态管理
 */
export const authManager = {
  // 检查用户是否已登录
  isAuthenticated() {
    const token = tokenStorage.getToken()
    if (!token) return false
    
    if (!tokenValidator.validateTokenFormat(token)) {
      this.logout()
      return false
    }
    
    if (tokenValidator.isTokenExpired()) {
      this.logout()
      return false
    }
    
    return true
  },

  // 用户登录处理
  async login(loginResponse) {
    try {
      const { token, refresh_token, user, expires_in } = loginResponse
      
      // 验证响应数据
      if (!token || !user) {
        throw new Error('登录响应数据不完整')
      }
      
      // 计算过期时间
      const expiresAt = Math.floor(Date.now() / 1000) + expires_in
      
      // 存储Token和用户信息
      tokenStorage.setToken(token)
      tokenStorage.setTokenExpire(expiresAt)
      if (refresh_token) {
        tokenStorage.setRefreshToken(refresh_token)
      }
      userStorage.setUserInfo(user)
      
      console.log('✅ 用户登录成功:', user.username)
      return true
      
    } catch (error) {
      console.error('❌ 登录处理失败:', error)
      return false
    }
  },

  // 用户登出处理
  logout() {
    tokenStorage.clearTokens()
    userStorage.clearUserInfo()
    console.log('🔴 用户已登出')
    
    // 如果当前页面不是登录页，跳转到登录页
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  },

  // 刷新Token
  async refreshToken() {
    const refreshToken = tokenStorage.getRefreshToken()
    if (!refreshToken) {
      this.logout()
      return false
    }
    
    try {
      // 这里需要调用API刷新Token (在api.js中实现)
      // const response = await api.post('/auth/refresh', { refresh_token: refreshToken })
      // const newTokenData = response.data
      // return await this.login(newTokenData)
      
      console.log('🔄 Token刷新功能待api.js实现')
      return false
      
    } catch (error) {
      console.error('❌ Token刷新失败:', error)
      this.logout()
      return false
    }
  }
}

/**
 * 🛡️ 路由守卫工具
 */
export const routeGuard = {
  // 检查路由权限
  checkRoutePermission(route) {
    // 检查是否需要登录
    if (route.meta?.requiresAuth !== false) {
      if (!authManager.isAuthenticated()) {
        return { allowed: false, redirect: '/login' }
      }
    }
    
    // 检查路由权限
    const permissions = route.meta?.permissions
    if (permissions && permissions.length > 0) {
      if (!permissionChecker.hasAnyPermission(permissions)) {
        return { allowed: false, redirect: '/403' }
      }
    }
    
    // 检查角色权限
    const roles = route.meta?.roles
    if (roles && roles.length > 0) {
      if (!permissionChecker.hasAnyRole(roles)) {
        return { allowed: false, redirect: '/403' }
      }
    }
    
    return { allowed: true }
  },

  // 全局路由守卫
  beforeRouteEnter(to, from, next) {
    const result = this.checkRoutePermission(to)
    
    if (result.allowed) {
      next()
    } else {
      next(result.redirect)
    }
  }
}

/**
 * 🧹 清理工具
 */
export const authCleaner = {
  // 清理所有认证数据
  clearAll() {
    tokenStorage.clearTokens()
    userStorage.clearUserInfo()
  },

  // 清理过期的数据
  clearExpired() {
    if (tokenValidator.isTokenExpired()) {
      this.clearAll()
    }
  }
}

// 🚀 默认导出
export default {
  tokenStorage,
  userStorage,
  tokenValidator,
  permissionChecker,
  authManager,
  routeGuard,
  authCleaner
}

/**
 * 🔧 工具函数
 */

// 获取当前用户信息的快捷方法
export const getCurrentUser = () => userStorage.getUserInfo()

// 检查权限的快捷方法
export const can = (permission) => permissionChecker.hasPermission(permission)

// 检查角色的快捷方法
export const is = (role) => permissionChecker.hasRole(role)

// 检查登录状态的快捷方法
export const isLoggedIn = () => authManager.isAuthenticated()