#!/usr/bin/env javascript
/**
 * API调用封装模块
 * 统一处理HTTP请求、Token管理、错误处理和响应拦截
 * 支持自动Token刷新和重试机制
 */

import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { tokenStorage, authManager } from './auth.js'

// 🌐 API基础配置
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://your-domain.com/api'  // 生产环境API地址
  : 'http://localhost:8000/api'    // 开发环境API地址

const REQUEST_TIMEOUT = 30000  // 30秒超时
const RETRY_COUNT = 3          // 重试次数

/**
 * 🔧 创建axios实例
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

/**
 * 📤 请求拦截器
 */
apiClient.interceptors.request.use(
  (config) => {
    // 添加认证Token
    const token = tokenStorage.getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 添加请求时间戳 (用于调试)
    config.metadata = { startTime: Date.now() }
    
    console.log(`🚀 API请求: ${config.method?.toUpperCase()} ${config.url}`)
    
    return config
  },
  (error) => {
    console.error('❌ 请求配置错误:', error)
    return Promise.reject(error)
  }
)

/**
 * 📥 响应拦截器
 */
apiClient.interceptors.response.use(
  (response) => {
    // 计算请求耗时
    if (response.config.metadata) {
      const duration = Date.now() - response.config.metadata.startTime
      console.log(`✅ API响应: ${response.config.method?.toUpperCase()} ${response.config.url} (${duration}ms)`)
    }
    
    return response
  },
  async (error) => {
    const { config, response } = error
    
    // 计算请求耗时
    if (config?.metadata) {
      const duration = Date.now() - config.metadata.startTime
      console.error(`❌ API错误: ${config.method?.toUpperCase()} ${config.url} (${duration}ms)`)
    }
    
    // 401 未授权处理
    if (response?.status === 401) {
      console.warn('🔒 认证失效，尝试刷新Token...')
      
      // 避免在登录/刷新接口上重试
      if (!config.url?.includes('/auth/login') && !config.url?.includes('/auth/refresh')) {
        const refreshed = await authManager.refreshToken()
        
        if (refreshed) {
          // Token刷新成功，重试原请求
          const newToken = tokenStorage.getToken()
          config.headers.Authorization = `Bearer ${newToken}`
          return apiClient.request(config)
        } else {
          // Token刷新失败，跳转登录
          ElMessage.error('登录已过期，请重新登录')
          authManager.logout()
          return Promise.reject(error)
        }
      }
    }
    
    // 403 权限不足
    if (response?.status === 403) {
      ElMessage.error('权限不足，无法执行此操作')
    }
    
    // 404 资源不存在
    if (response?.status === 404) {
      ElMessage.error('请求的资源不存在')
    }
    
    // 500 服务器错误
    if (response?.status >= 500) {
      ElMessage.error('服务器错误，请稍后重试')
    }
    
    // 网络错误
    if (!response) {
      ElMessage.error('网络连接失败，请检查网络')
    }
    
    return Promise.reject(error)
  }
)

/**
 * 🎯 统一API请求封装
 */
class ApiClient {
  /**
   * GET请求
   */
  async get(url, params = {}, config = {}) {
    try {
      const response = await apiClient.get(url, {
        params,
        ...config
      })
      return this.handleResponse(response)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  /**
   * POST请求
   */
  async post(url, data = {}, config = {}) {
    try {
      const response = await apiClient.post(url, data, config)
      return this.handleResponse(response)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  /**
   * PUT请求
   */
  async put(url, data = {}, config = {}) {
    try {
      const response = await apiClient.put(url, data, config)
      return this.handleResponse(response)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  /**
   * PATCH请求
   */
  async patch(url, data = {}, config = {}) {
    try {
      const response = await apiClient.patch(url, data, config)
      return this.handleResponse(response)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  /**
   * DELETE请求
   */
  async delete(url, config = {}) {
    try {
      const response = await apiClient.delete(url, config)
      return this.handleResponse(response)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  /**
   * 文件上传
   */
  async upload(url, file, progressCallback = null, config = {}) {
    const formData = new FormData()
    formData.append('file', file)
    
    const uploadConfig = {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (progressCallback) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          progressCallback(percentCompleted)
        }
      },
      ...config
    }
    
    try {
      const response = await apiClient.post(url, formData, uploadConfig)
      return this.handleResponse(response)
    } catch (error) {
      throw this.handleError(error)
    }
  }

  /**
   * 文件下载
   */
  async download(url, filename, config = {}) {
    try {
      const response = await apiClient.get(url, {
        responseType: 'blob',
        ...config
      })
      
      // 创建下载链接
      const blob = new Blob([response.data])
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
      
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  /**
   * 响应处理
   */
  handleResponse(response) {
    const { data, status } = response
    
    // 标准成功响应格式
    if (status >= 200 && status < 300) {
      return {
        data: data.data || data,
        message: data.message || 'success',
        code: data.code || status,
        success: true
      }
    }
    
    return data
  }

  /**
   * 错误处理
   */
  handleError(error) {
    const { response, message } = error
    
    if (response) {
      // 服务器返回错误
      const errorData = response.data || {}
      return {
        data: null,
        message: errorData.message || errorData.detail || '请求失败',
        code: response.status,
        success: false,
        error: errorData
      }
    } else {
      // 网络错误或请求超时
      return {
        data: null,
        message: message || '网络连接失败',
        code: 0,
        success: false,
        error: { message }
      }
    }
  }
}

// 创建API客户端实例
const api = new ApiClient()

/**
 * 🔐 认证相关API
 */
export const authApi = {
  // 用户登录
  async login(credentials) {
    return await api.post('/auth/login', credentials)
  },

  // 用户登出
  async logout() {
    return await api.post('/auth/logout')
  },

  // 刷新Token
  async refreshToken(refreshToken) {
    return await api.post('/auth/refresh', { refresh_token: refreshToken })
  },

  // 获取当前用户信息
  async getCurrentUser() {
    return await api.get('/auth/me')
  },

  // 修改密码
  async changePassword(data) {
    return await api.put('/auth/password', data)
  }
}

/**
 * 📋 项目管理API
 */
export const projectApi = {
  // 获取项目列表
  async getProjects(params = {}) {
    return await api.get('/projects', params)
  },

  // 获取项目详情
  async getProject(id) {
    return await api.get(`/projects/${id}`)
  },

  // 创建项目
  async createProject(data) {
    return await api.post('/projects', data)
  },

  // 更新项目
  async updateProject(id, data) {
    return await api.put(`/projects/${id}`, data)
  },

  // 删除项目
  async deleteProject(id) {
    return await api.delete(`/projects/${id}`)
  },

  // 更新项目状态
  async updateProjectStatus(id, status) {
    return await api.patch(`/projects/${id}/status`, { status })
  },

  // 上传项目文件
  async uploadFile(projectId, file, progressCallback) {
    return await api.upload(`/projects/${projectId}/files`, file, progressCallback)
  },

  // 获取项目文件列表
  async getProjectFiles(projectId) {
    return await api.get(`/projects/${projectId}/files`)
  },

  // 删除项目文件
  async deleteFile(projectId, fileId) {
    return await api.delete(`/projects/${projectId}/files/${fileId}`)
  }
}

/**
 * ✅ 任务管理API
 */
export const taskApi = {
  // 获取任务列表
  async getTasks(params = {}) {
    return await api.get('/tasks', params)
  },

  // 获取任务详情
  async getTask(id) {
    return await api.get(`/tasks/${id}`)
  },

  // 创建任务
  async createTask(data) {
    return await api.post('/tasks', data)
  },

  // 更新任务
  async updateTask(id, data) {
    return await api.put(`/tasks/${id}`, data)
  },

  // 删除任务
  async deleteTask(id) {
    return await api.delete(`/tasks/${id}`)
  },

  // 完成任务
  async completeTask(id) {
    return await api.patch(`/tasks/${id}/complete`)
  }
}

/**
 * 🏢 供应商管理API
 */
export const supplierApi = {
  // 获取供应商列表
  async getSuppliers(params = {}) {
    return await api.get('/suppliers', params)
  },

  // 获取供应商详情
  async getSupplier(id) {
    return await api.get(`/suppliers/${id}`)
  },

  // 创建供应商
  async createSupplier(data) {
    return await api.post('/suppliers', data)
  },

  // 更新供应商
  async updateSupplier(id, data) {
    return await api.put(`/suppliers/${id}`, data)
  },

  // 删除供应商
  async deleteSupplier(id) {
    return await api.delete(`/suppliers/${id}`)
  }
}

/**
 * 👥 用户管理API
 */
export const userApi = {
  // 获取用户列表
  async getUsers(params = {}) {
    return await api.get('/users', params)
  },

  // 获取用户详情
  async getUser(id) {
    return await api.get(`/users/${id}`)
  },

  // 创建用户
  async createUser(data) {
    return await api.post('/users', data)
  },

  // 更新用户
  async updateUser(id, data) {
    return await api.put(`/users/${id}`, data)
  },

  // 删除用户
  async deleteUser(id) {
    return await api.delete(`/users/${id}`)
  },

  // 获取设计师列表
  async getDesigners() {
    return await api.get('/users/designers')
  }
}

/**
 * 💰 财务管理API
 */
export const financeApi = {
  // 获取财务记录
  async getFinanceRecords(params = {}) {
    return await api.get('/finance/records', params)
  },

  // 创建财务记录
  async createFinanceRecord(data) {
    return await api.post('/finance/records', data)
  },

  // 更新财务记录
  async updateFinanceRecord(id, data) {
    return await api.put(`/finance/records/${id}`, data)
  },

  // 获取财务统计
  async getFinanceStatistics(params = {}) {
    return await api.get('/finance/statistics', params)
  }
}

/**
 * 📊 报告管理API
 */
export const reportApi = {
  // 获取仪表盘数据
  async getDashboardData() {
    return await api.get('/reports/dashboard')
  },

  // 获取项目统计
  async getProjectStatistics(params = {}) {
    return await api.get('/reports/projects', params)
  },

  // 获取财务报告
  async getFinanceReport(params = {}) {
    return await api.get('/reports/finance', params)
  },

  // 获取用户效率报告
  async getUserEfficiencyReport(params = {}) {
    return await api.get('/reports/user-efficiency', params)
  }
}

/**
 * ⚙️ 系统配置API
 */
export const systemApi = {
  // 获取系统配置
  async getSystemConfig() {
    return await api.get('/system/config')
  },

  // 更新系统配置
  async updateSystemConfig(data) {
    return await api.put('/system/config', data)
  },

  // 获取系统状态
  async getSystemStatus() {
    return await api.get('/system/status')
  },

  // 系统健康检查
  async healthCheck() {
    return await api.get('/health')
  }
}

/**
 * 🤖 AI服务API
 */
export const aiApi = {
  // OCR图像识别
  async ocrImage(file, progressCallback) {
    return await api.upload('/ai/ocr', file, progressCallback)
  },

  // 获取AI对话历史
  async getConversations(params = {}) {
    return await api.get('/ai/conversations', params)
  },

  // 发送AI消息
  async sendMessage(data) {
    return await api.post('/ai/message', data)
  }
}

/**
 * 🛠️ 工具函数
 */
export const apiUtils = {
  // 构建查询参数
  buildParams(obj) {
    const params = new URLSearchParams()
    Object.keys(obj).forEach(key => {
      if (obj[key] !== null && obj[key] !== undefined && obj[key] !== '') {
        params.append(key, obj[key])
      }
    })
    return params.toString()
  },

  // 处理分页参数
  buildPaginationParams(page = 1, pageSize = 20, filters = {}) {
    return {
      page,
      page_size: pageSize,
      ...filters
    }
  },

  // 格式化错误消息
  formatErrorMessage(error) {
    if (typeof error === 'string') return error
    if (error?.message) return error.message
    if (error?.detail) return error.detail
    return '未知错误'
  }
}

// 默认导出
export default api

// 导出所有API模块
export {
  api,
  apiClient,
  authApi,
  projectApi,
  taskApi,
  supplierApi,
  userApi,
  financeApi,
  reportApi,
  systemApi,
  aiApi,
  apiUtils
}