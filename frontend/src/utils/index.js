#!/usr/bin/env javascript
/**
 * Pinia状态管理主文件
 * 统一管理应用的状态存储，包括用户、项目、任务等模块
 * 支持数据持久化和响应式更新
 */

import { createPinia } from 'pinia'
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

// API导入
import {
  authApi,
  projectApi,
  taskApi,
  userApi,
  supplierApi,
  financeApi,
  reportApi
} from '@/utils/api.js'

// 认证工具导入
import {
  authManager,
  userStorage,
  tokenStorage,
  permissionChecker
} from '@/utils/auth.js'

/**
 * 🔐 用户状态管理
 */
export const useUserStore = defineStore('user', () => {
  // 状态
  const user = ref(null)
  const isLoggedIn = ref(false)
  const permissions = ref([])
  const loading = ref(false)

  // 计算属性
  const userRole = computed(() => user.value?.role || null)
  const userName = computed(() => user.value?.username || '未知用户')
  const userAvatar = computed(() => user.value?.avatar || '/default-avatar.png')
  const isAdmin = computed(() => userRole.value === 'admin')
  const isDesigner = computed(() => userRole.value === 'designer')
  const isFinance = computed(() => userRole.value === 'finance')

  // 动作
  const loadUserFromStorage = () => {
    const storedUser = userStorage.getUserInfo()
    const hasToken = tokenStorage.hasToken()
    
    if (storedUser && hasToken && authManager.isAuthenticated()) {
      user.value = storedUser
      isLoggedIn.value = true
      permissions.value = userStorage.getUserPermissions()
      console.log('✅ 从本地存储加载用户信息:', storedUser.username)
    } else {
      clearUser()
    }
  }

  const login = async (credentials) => {
    loading.value = true
    try {
      const response = await authApi.login(credentials)
      
      if (response.success) {
        const loginSuccess = await authManager.login(response.data)
        
        if (loginSuccess) {
          await loadCurrentUser()
          ElMessage.success('登录成功')
          return true
        }
      }
      
      ElMessage.error(response.message || '登录失败')
      return false
      
    } catch (error) {
      ElMessage.error('登录失败: ' + error.message)
      return false
    } finally {
      loading.value = false
    }
  }

  const logout = async () => {
    loading.value = true
    try {
      // 调用后端登出API
      await authApi.logout()
    } catch (error) {
      console.warn('后端登出失败:', error)
    } finally {
      // 无论如何都清理本地状态
      authManager.logout()
      clearUser()
      loading.value = false
      ElMessage.success('已退出登录')
    }
  }

  const loadCurrentUser = async () => {
    try {
      const response = await authApi.getCurrentUser()
      
      if (response.success) {
        user.value = response.data
        isLoggedIn.value = true
        permissions.value = response.data.permissions || []
        userStorage.setUserInfo(response.data)
      }
      
    } catch (error) {
      console.error('加载用户信息失败:', error)
      clearUser()
    }
  }

  const updateProfile = async (profileData) => {
    loading.value = true
    try {
      const response = await userApi.updateUser(user.value.id, profileData)
      
      if (response.success) {
        user.value = { ...user.value, ...response.data }
        userStorage.setUserInfo(user.value)
        ElMessage.success('资料更新成功')
        return true
      }
      
      ElMessage.error(response.message || '更新失败')
      return false
      
    } catch (error) {
      ElMessage.error('更新失败: ' + error.message)
      return false
    } finally {
      loading.value = false
    }
  }

  const changePassword = async (passwordData) => {
    loading.value = true
    try {
      const response = await authApi.changePassword(passwordData)
      
      if (response.success) {
        ElMessage.success('密码修改成功')
        return true
      }
      
      ElMessage.error(response.message || '密码修改失败')
      return false
      
    } catch (error) {
      ElMessage.error('密码修改失败: ' + error.message)
      return false
    } finally {
      loading.value = false
    }
  }

  const clearUser = () => {
    user.value = null
    isLoggedIn.value = false
    permissions.value = []
  }

  const hasPermission = (permission) => {
    return permissionChecker.hasPermission(permission)
  }

  const hasRole = (role) => {
    return userRole.value === role
  }

  // 获取设计师列表 (供其他组件使用)
  const fetchDesigners = async () => {
    try {
      const response = await userApi.getDesigners()
      return response.success ? response.data : []
    } catch (error) {
      console.error('获取设计师列表失败:', error)
      return []
    }
  }

  return {
    // 状态
    user,
    isLoggedIn,
    permissions,
    loading,
    // 计算属性
    userRole,
    userName,
    userAvatar,
    isAdmin,
    isDesigner,
    isFinance,
    // 动作
    loadUserFromStorage,
    login,
    logout,
    loadCurrentUser,
    updateProfile,
    changePassword,
    clearUser,
    hasPermission,
    hasRole,
    fetchDesigners
  }
}, {
  persist: false // 不持久化，使用auth.js管理存储
})

/**
 * 📋 项目状态管理
 */
export const useProjectStore = defineStore('project', () => {
  // 状态
  const projects = ref([])
  const currentProject = ref(null)
  const loading = ref(false)
  const pagination = ref({
    page: 1,
    pageSize: 20,
    total: 0
  })

  // 动作
  const fetchProjects = async (params = {}) => {
    loading.value = true
    try {
      const response = await projectApi.getProjects({
        page: pagination.value.page,
        page_size: pagination.value.pageSize,
        ...params
      })
      
      if (response.success) {
        projects.value = response.data.items || response.data
        if (response.data.total !== undefined) {
          pagination.value.total = response.data.total
        }
        return response.data
      }
      
      ElMessage.error(response.message || '获取项目列表失败')
      return { items: [], total: 0 }
      
    } catch (error) {
      ElMessage.error('获取项目列表失败: ' + error.message)
      return { items: [], total: 0 }
    } finally {
      loading.value = false
    }
  }

  const fetchProject = async (id) => {
    loading.value = true
    try {
      const response = await projectApi.getProject(id)
      
      if (response.success) {
        currentProject.value = response.data
        return response.data
      }
      
      ElMessage.error(response.message || '获取项目详情失败')
      return null
      
    } catch (error) {
      ElMessage.error('获取项目详情失败: ' + error.message)
      return null
    } finally {
      loading.value = false
    }
  }

  const createProject = async (projectData) => {
    loading.value = true
    try {
      const response = await projectApi.createProject(projectData)
      
      if (response.success) {
        // 更新本地项目列表
        projects.value.unshift(response.data)
        ElMessage.success('项目创建成功')
        return response.data
      }
      
      ElMessage.error(response.message || '项目创建失败')
      return null
      
    } catch (error) {
      ElMessage.error('项目创建失败: ' + error.message)
      return null
    } finally {
      loading.value = false
    }
  }

  const updateProject = async (id, projectData) => {
    loading.value = true
    try {
      const response = await projectApi.updateProject(id, projectData)
      
      if (response.success) {
        // 更新本地项目数据
        const index = projects.value.findIndex(p => p.id === id)
        if (index !== -1) {
          projects.value[index] = response.data
        }
        
        if (currentProject.value?.id === id) {
          currentProject.value = response.data
        }
        
        ElMessage.success('项目更新成功')
        return response.data
      }
      
      ElMessage.error(response.message || '项目更新失败')
      return null
      
    } catch (error) {
      ElMessage.error('项目更新失败: ' + error.message)
      return null
    } finally {
      loading.value = false
    }
  }

  const deleteProject = async (id) => {
    loading.value = true
    try {
      const response = await projectApi.deleteProject(id)
      
      if (response.success) {
        // 从本地列表移除
        projects.value = projects.value.filter(p => p.id !== id)
        
        if (currentProject.value?.id === id) {
          currentProject.value = null
        }
        
        ElMessage.success('项目删除成功')
        return true
      }
      
      ElMessage.error(response.message || '项目删除失败')
      return false
      
    } catch (error) {
      ElMessage.error('项目删除失败: ' + error.message)
      return false
    } finally {
      loading.value = false
    }
  }

  const updateProjectStatus = async (id, status) => {
    try {
      const response = await projectApi.updateProjectStatus(id, status)
      
      if (response.success) {
        // 更新本地状态
        const index = projects.value.findIndex(p => p.id === id)
        if (index !== -1) {
          projects.value[index].status = status
        }
        
        if (currentProject.value?.id === id) {
          currentProject.value.status = status
        }
        
        return true
      }
      
      ElMessage.error(response.message || '状态更新失败')
      return false
      
    } catch (error) {
      ElMessage.error('状态更新失败: ' + error.message)
      return false
    }
  }

  return {
    // 状态
    projects,
    currentProject,
    loading,
    pagination,
    // 动作
    fetchProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject,
    updateProjectStatus
  }
})

/**
 * ✅ 任务状态管理
 */
export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const currentTask = ref(null)
  const loading = ref(false)

  const fetchTasks = async (params = {}) => {
    loading.value = true
    try {
      const response = await taskApi.getTasks(params)
      
      if (response.success) {
        tasks.value = response.data.items || response.data
        return response.data
      }
      
      return { items: [], total: 0 }
      
    } catch (error) {
      ElMessage.error('获取任务列表失败: ' + error.message)
      return { items: [], total: 0 }
    } finally {
      loading.value = false
    }
  }

  const createTask = async (taskData) => {
    loading.value = true
    try {
      const response = await taskApi.createTask(taskData)
      
      if (response.success) {
        tasks.value.unshift(response.data)
        ElMessage.success('任务创建成功')
        return response.data
      }
      
      ElMessage.error(response.message || '任务创建失败')
      return null
      
    } catch (error) {
      ElMessage.error('任务创建失败: ' + error.message)
      return null
    } finally {
      loading.value = false
    }
  }

  const updateTask = async (id, taskData) => {
    loading.value = true
    try {
      const response = await taskApi.updateTask(id, taskData)
      
      if (response.success) {
        const index = tasks.value.findIndex(t => t.id === id)
        if (index !== -1) {
          tasks.value[index] = response.data
        }
        
        ElMessage.success('任务更新成功')
        return response.data
      }
      
      ElMessage.error(response.message || '任务更新失败')
      return null
      
    } catch (error) {
      ElMessage.error('任务更新失败: ' + error.message)
      return null
    } finally {
      loading.value = false
    }
  }

  const completeTask = async (id) => {
    try {
      const response = await taskApi.completeTask(id)
      
      if (response.success) {
        const index = tasks.value.findIndex(t => t.id === id)
        if (index !== -1) {
          tasks.value[index].is_completed = true
        }
        
        ElMessage.success('任务已完成')
        return true
      }
      
      return false
      
    } catch (error) {
      ElMessage.error('完成任务失败: ' + error.message)
      return false
    }
  }

  return {
    tasks,
    currentTask,
    loading,
    fetchTasks,
    createTask,
    updateTask,
    completeTask
  }
})

/**
 * 📊 报告状态管理
 */
export const useReportStore = defineStore('report', () => {
  const dashboardData = ref(null)
  const loading = ref(false)

  const fetchDashboardData = async () => {
    loading.value = true
    try {
      const response = await reportApi.getDashboardData()
      
      if (response.success) {
        dashboardData.value = response.data
        return response.data
      }
      
      return null
      
    } catch (error) {
      console.error('获取仪表盘数据失败:', error)
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    dashboardData,
    loading,
    fetchDashboardData
  }
})

/**
 * ⚙️ 应用状态管理
 */
export const useAppStore = defineStore('app', () => {
  // 状态
  const sidebarCollapsed = ref(false)
  const theme = ref('light')
  const language = ref('zh-CN')
  const loading = ref(false)

  // 动作
  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  const setSidebarCollapsed = (collapsed) => {
    sidebarCollapsed.value = collapsed
  }

  const setTheme = (newTheme) => {
    theme.value = newTheme
    document.documentElement.setAttribute('data-theme', newTheme)
  }

  const setLanguage = (lang) => {
    language.value = lang
  }

  const setLoading = (state) => {
    loading.value = state
  }

  return {
    // 状态
    sidebarCollapsed,
    theme,
    language,
    loading,
    // 动作
    toggleSidebar,
    setSidebarCollapsed,
    setTheme,
    setLanguage,
    setLoading
  }
}, {
  persist: {
    storage: localStorage,
    paths: ['sidebarCollapsed', 'theme', 'language']
  }
})

/**
 * 🏪 创建并配置Pinia
 */
export const pinia = createPinia()

// Pinia持久化插件 (可选)
const piniaPersistedState = {
  install: (app) => {
    // 简单的持久化实现
    app.config.globalProperties.$persist = (store, options = {}) => {
      const { storage = localStorage, paths = [] } = options
      
      // 从存储加载状态
      const savedState = storage.getItem(store.$id)
      if (savedState) {
        try {
          const parsedState = JSON.parse(savedState)
          if (paths.length > 0) {
            paths.forEach(path => {
              if (parsedState[path] !== undefined) {
                store[path] = parsedState[path]
              }
            })
          } else {
            store.$patch(parsedState)
          }
        } catch (error) {
          console.warn('恢复状态失败:', error)
        }
      }
      
      // 监听状态变化并保存
      store.$subscribe((mutation, state) => {
        const stateToSave = paths.length > 0 
          ? paths.reduce((acc, path) => {
              acc[path] = state[path]
              return acc
            }, {})
          : state
          
        storage.setItem(store.$id, JSON.stringify(stateToSave))
      })
    }
  }
}

// 注册插件
pinia.use(piniaPersistedState)

export default pinia

/**
 * 🎯 统一导出所有Store
 */
export {
  useUserStore,
  useProjectStore,
  useTaskStore,
  useReportStore,
  useAppStore
}