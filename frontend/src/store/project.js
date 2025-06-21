import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectApi, reportApi } from '@/utils/api'
import { ElMessage } from 'element-plus'

export const useProjectStore = defineStore('project', () => {
  // 状态
  const projects = ref([])
  const currentProject = ref(null)
  const loading = ref(false)
  const statistics = ref({
    total: 0,
    ongoing: 0,
    completed: 0,
    overdue: 0,
    monthlyCompleted: 0,
    pendingTasks: 0
  })
  
  // 计算属性
  const projectCount = computed(() => projects.value.length)
  const ongoingProjects = computed(() => 
    projects.value.filter(p => ['设计中', '生产中', '待确认'].includes(p.status))
  )
  const completedProjects = computed(() => 
    projects.value.filter(p => p.status === '已完成')
  )
  
  // 方法
  
  // 获取项目列表
  const fetchProjects = async (params = {}) => {
    loading.value = true
    try {
      const response = await projectApi.getProjects(params)
      
      if (response.success) {
        projects.value = response.data
        return {
          items: response.data,
          total: response.meta?.total || response.data.length,
          page: response.meta?.page || 1,
          pageSize: response.meta?.page_size || 20
        }
      }
      
      return { items: [], total: 0, page: 1, pageSize: 20 }
      
    } catch (error) {
      ElMessage.error('获取项目列表失败')
      return { items: [], total: 0, page: 1, pageSize: 20 }
    } finally {
      loading.value = false
    }
  }
  
  // 获取项目详情
  const fetchProjectDetail = async (id) => {
    loading.value = true
    try {
      const response = await projectApi.getProject(id)
      
      if (response.success) {
        currentProject.value = response.data
        return response.data
      }
      
      return null
      
    } catch (error) {
      ElMessage.error('获取项目详情失败')
      return null
    } finally {
      loading.value = false
    }
  }
  
  // 创建项目
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
  
  // 更新项目
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
  
  // 删除项目
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
  
  // 更新项目状态
  const updateProjectStatus = async (id, status) => {
    loading.value = true
    try {
      const response = await projectApi.updateProjectStatus(id, status)
      
      if (response.success) {
        // 更新本地数据
        const project = projects.value.find(p => p.id === id)
        if (project) {
          project.status = status
        }
        
        if (currentProject.value?.id === id) {
          currentProject.value.status = status
        }
        
        ElMessage.success('状态更新成功')
        return true
      }
      
      ElMessage.error(response.message || '状态更新失败')
      return false
      
    } catch (error) {
      ElMessage.error('状态更新失败: ' + error.message)
      return false
    } finally {
      loading.value = false
    }
  }
  
  // 获取项目统计
  const fetchStatistics = async () => {
    try {
      const response = await reportApi.getProjectStatistics()
      
      if (response.success) {
        statistics.value = response.data
        return response.data
      }
      
      return null
      
    } catch (error) {
      console.error('获取项目统计失败:', error)
      return null
    }
  }
  
  // 上传项目文件
  const uploadProjectFile = async (projectId, file, progressCallback) => {
    try {
      const response = await projectApi.uploadFile(projectId, file, progressCallback)
      
      if (response.success) {
        ElMessage.success('文件上传成功')
        return response.data
      }
      
      ElMessage.error(response.message || '文件上传失败')
      return null
      
    } catch (error) {
      ElMessage.error('文件上传失败: ' + error.message)
      return null
    }
  }
  
  // 清空数据
  const clearData = () => {
    projects.value = []
    currentProject.value = null
    statistics.value = {
      total: 0,
      ongoing: 0,
      completed: 0,
      overdue: 0,
      monthlyCompleted: 0,
      pendingTasks: 0
    }
  }
  
  return {
    // 状态
    projects,
    currentProject,
    loading,
    statistics,
    
    // 计算属性
    projectCount,
    ongoingProjects,
    completedProjects,
    
    // 方法
    fetchProjects,
    fetchProjectDetail,
    createProject,
    updateProject,
    deleteProject,
    updateProjectStatus,
    fetchStatistics,
    uploadProjectFile,
    clearData
  }
})