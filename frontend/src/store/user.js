import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, userApi } from '@/utils/api'
import { tokenStorage, userStorage } from '@/utils/auth'
import { ElMessage } from 'element-plus'

export const useUserStore = defineStore('user', () => {
  // 状态
  const user = ref(null)
  const permissions = ref([])
  const teamCount = ref(0)
  const designers = ref([])
  
  // 计算属性
  const isLoggedIn = computed(() => !!user.value && tokenStorage.hasToken())
  const userId = computed(() => user.value?.id)
  const username = computed(() => user.value?.username)
  const role = computed(() => user.value?.role)
  const isAdmin = computed(() => user.value?.role === 'admin' || user.value?.is_admin)
  const fullName = computed(() => user.value?.full_name || user.value?.username)
  
  // 方法
  
  // 设置用户信息
  const setUser = (userInfo) => {
    user.value = userInfo
    userStorage.setUserInfo(userInfo)
    
    // 根据角色设置权限
    if (userInfo) {
      setPermissionsByRole(userInfo.role)
    }
  }
  
  // 根据角色设置权限
  const setPermissionsByRole = (role) => {
    const rolePermissions = {
      admin: [
        'project:read', 'project:create', 'project:update', 'project:delete',
        'task:read', 'task:create', 'task:update', 'task:delete',
        'supplier:read', 'supplier:create', 'supplier:update', 'supplier:delete',
        'user:read', 'user:create', 'user:update', 'user:delete',
        'finance:read', 'finance:update',
        'system:config', 'report:view'
      ],
      designer: [
        'project:read', 'project:update',
        'task:read', 'task:update',
        'supplier:read'
      ],
      finance: [
        'project:read',
        'finance:read', 'finance:update',
        'report:view'
      ],
      viewer: [
        'project:read',
        'task:read'
      ]
    }
    
    permissions.value = rolePermissions[role] || []
  }
  
  // 检查权限
  const hasPermission = (permission) => {
    if (isAdmin.value) return true
    return permissions.value.includes(permission)
  }
  
  // 检查多个权限（任一）
  const hasPermissions = (permissionList) => {
    if (isAdmin.value) return true
    return permissionList.some(p => permissions.value.includes(p))
  }
  
  // 检查多个权限（全部）
  const hasAllPermissions = (permissionList) => {
    if (isAdmin.value) return true
    return permissionList.every(p => permissions.value.includes(p))
  }
  
  // 获取当前用户信息
  const fetchCurrentUser = async () => {
    try {
      const response = await authApi.getCurrentUser()
      if (response.success) {
        setUser(response.data)
        return response.data
      }
      return null
    } catch (error) {
      console.error('获取用户信息失败:', error)
      return null
    }
  }
  
  // 更新用户信息
  const updateProfile = async (data) => {
    try {
      const response = await userApi.updateUser(userId.value, data)
      if (response.success) {
        setUser(response.data)
        ElMessage.success('个人信息更新成功')
        return true
      }
      return false
    } catch (error) {
      ElMessage.error('更新失败')
      return false
    }
  }
  
  // 修改密码
  const changePassword = async (oldPassword, newPassword) => {
    try {
      const response = await authApi.changePassword({
        old_password: oldPassword,
        new_password: newPassword
      })
      
      if (response.success) {
        ElMessage.success('密码修改成功，请重新登录')
        logout()
        return true
      }
      return false
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '密码修改失败')
      return false
    }
  }
  
  // 获取设计师列表
  const fetchDesigners = async () => {
    try {
      const response = await userApi.getDesigners()
      if (response.success) {
        designers.value = response.data
        return response.data
      }
      return []
    } catch (error) {
      console.error('获取设计师列表失败:', error)
      return []
    }
  }
  
  // 获取团队成员数量
  const fetchTeamCount = async () => {
    try {
      const response = await userApi.getUsers({ page_size: 1 })
      if (response.success) {
        teamCount.value = response.meta?.total || 0
        return teamCount.value
      }
      return 0
    } catch (error) {
      console.error('获取团队成员数量失败:', error)
      return 0
    }
  }
  
  // 登出
  const logout = () => {
    // 清除用户信息
    user.value = null
    permissions.value = []
    
    // 清除存储
    tokenStorage.clearTokens()
    userStorage.clearUserInfo()
    
    // 清除其他store数据
    // TODO: 清除其他store
  }
  
  // 初始化
  const init = async () => {
    // 从存储恢复用户信息
    const storedUser = userStorage.getUserInfo()
    if (storedUser && tokenStorage.hasToken()) {
      setUser(storedUser)
      
      // 尝试刷新用户信息
      await fetchCurrentUser()
    }
  }
  
  return {
    // 状态
    user,
    permissions,
    teamCount,
    designers,
    
    // 计算属性
    isLoggedIn,
    userId,
    username,
    role,
    isAdmin,
    fullName,
    
    // 方法
    setUser,
    hasPermission,
    hasPermissions,
    hasAllPermissions,
    fetchCurrentUser,
    updateProfile,
    changePassword,
    fetchDesigners,
    fetchTeamCount,
    logout,
    init
  }
})