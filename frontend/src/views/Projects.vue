<template>
  <div class="projects-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>项目管理</h1>
      <el-button type="primary" icon="Plus" @click="handleCreate">
        创建项目
      </el-button>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" @submit.prevent="handleSearch">
        <el-form-item label="项目名称">
          <el-input 
            v-model="filterForm.keyword" 
            placeholder="请输入项目名称或客户名称"
            clearable
            @clear="handleSearch"
          />
        </el-form-item>
        
        <el-form-item label="项目状态">
          <el-select 
            v-model="filterForm.status" 
            placeholder="全部状态"
            clearable
            @change="handleSearch"
          >
            <el-option 
              v-for="status in projectStatuses" 
              :key="status.value"
              :label="status.label"
              :value="status.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="负责人">
          <el-select 
            v-model="filterForm.designerId" 
            placeholder="全部负责人"
            clearable
            @change="handleSearch"
          >
            <el-option 
              v-for="user in designers" 
              :key="user.id"
              :label="user.nickname || user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="创建时间">
          <el-date-picker
            v-model="filterForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            @change="handleSearch"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleSearch">
            搜索
          </el-button>
          <el-button icon="Refresh" @click="handleReset">
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 视图切换 -->
    <div class="view-switch">
      <el-radio-group v-model="viewMode" @change="handleViewChange">
        <el-radio-button label="card">
          <el-icon><Grid /></el-icon>
          卡片视图
        </el-radio-button>
        <el-radio-button label="list">
          <el-icon><List /></el-icon>
          列表视图
        </el-radio-button>
      </el-radio-group>
      
      <div class="view-actions">
        <el-button link type="primary" icon="Download" @click="handleExport">
          导出数据
        </el-button>
      </div>
    </div>

    <!-- 项目列表 - 卡片视图 -->
    <div v-if="viewMode === 'card'" v-loading="loading" class="project-cards">
      <el-row :gutter="20">
        <el-col
          v-for="project in projects"
          :key="project.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <ProjectCard 
            :project="project"
            @click="handleView(project)"
            @edit="handleEdit(project)"
            @delete="handleDelete(project)"
            @status-change="handleStatusChange"
          />
        </el-col>
      </el-row>
      
      <!-- 空状态 -->
      <el-empty 
        v-if="!loading && projects.length === 0"
        description="暂无项目数据"
      >
        <el-button type="primary" @click="handleCreate">创建第一个项目</el-button>
      </el-empty>
    </div>

    <!-- 项目列表 - 表格视图 -->
    <el-card v-else v-loading="loading" class="table-card">
      <el-table 
        :data="projects" 
        style="width: 100%"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="id" label="ID" width="80" sortable="custom" />
        <el-table-column prop="projectName" label="项目名称" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="handleView(row)">
              {{ row.projectName }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="customerName" label="客户名称" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="totalPrice" label="项目金额" width="120" sortable="custom">
          <template #default="{ row }">
            ¥{{ formatMoney(row.totalPrice) }}
          </template>
        </el-table-column>
        <el-table-column prop="designerName" label="负责人" width="100" />
        <el-table-column prop="createdAt" label="创建时间" width="180" sortable="custom">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">
              查看
            </el-button>
            <el-button link type="primary" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-popconfirm
              title="确定删除这个项目吗？"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handlePageSizeChange"
        @current-change="handlePageChange"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import ProjectCard from '@/components/ProjectCard.vue'
import { useProjectStore } from '@/stores/project'
import { useUserStore } from '@/stores/user'
import { Grid, List } from '@element-plus/icons-vue'

const router = useRouter()
const projectStore = useProjectStore()
const userStore = useUserStore()

// 响应式数据
const loading = ref(false)
const viewMode = ref('card')
const projects = ref([])
const designers = ref([])

const filterForm = reactive({
  keyword: '',
  status: '',
  designerId: null,
  dateRange: []
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const projectStatuses = [
  { label: '全部状态', value: '' },
  { label: '待报价', value: '待报价' },
  { label: '设计中', value: '设计中' },
  { label: '待确认', value: '待确认' },
  { label: '生产中', value: '生产中' },
  { label: '待收款', value: '待收款' },
  { label: '已完成', value: '已完成' },
  { label: '已取消', value: '已取消' }
]

// 方法
const loadProjects = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      pageSize: pagination.pageSize,
      keyword: filterForm.keyword,
      status: filterForm.status,
      designerId: filterForm.designerId
    }
    
    if (filterForm.dateRange?.length === 2) {
      params.startDate = filterForm.dateRange[0]
      params.endDate = filterForm.dateRange[1]
    }
    
    const res = await projectStore.fetchProjects(params)
    projects.value = res.items
    pagination.total = res.total
  } catch (error) {
    ElMessage.error('加载项目列表失败')
  } finally {
    loading.value = false
  }
}

const loadDesigners = async () => {
  try {
    const res = await userStore.fetchDesigners()
    designers.value = res
  } catch (error) {
    console.error('加载设计师列表失败:', error)
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadProjects()
}

const handleReset = () => {
  filterForm.keyword = ''
  filterForm.status = ''
  filterForm.designerId = null
  filterForm.dateRange = []
  handleSearch()
}

const handleCreate = () => {
  router.push('/projects/create')
}

const handleView = (project) => {
  router.push(`/projects/${project.id}`)
}

const handleEdit = (project) => {
  router.push(`/projects/${project.id}/edit`)
}

const handleDelete = async (project) => {
  try {
    await projectStore.deleteProject(project.id)
    ElMessage.success('删除成功')
    loadProjects()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const handleStatusChange = async ({ projectId, status }) => {
  try {
    await projectStore.updateProjectStatus(projectId, status)
    ElMessage.success('状态更新成功')
    loadProjects()
  } catch (error) {
    ElMessage.error('状态更新失败')
  }
}

const handleViewChange = () => {
  localStorage.setItem('projectViewMode', viewMode.value)
}

const handlePageChange = () => {
  loadProjects()
}

const handlePageSizeChange = () => {
  pagination.page = 1
  loadProjects()
}

const handleSortChange = ({ prop, order }) => {
  // 实现排序逻辑
  console.log('排序:', prop, order)
}

const handleExport = async () => {
  try {
    await ElMessageBox.confirm('确定要导出当前筛选条件下的所有项目数据吗？', '导出确认')
    // 实现导出逻辑
    ElMessage.success('导出功能开发中...')
  } catch {
    // 用户取消
  }
}

// 工具函数
const getStatusType = (status) => {
  const typeMap = {
    '待报价': 'info',
    '设计中': 'warning',
    '待确认': '',
    '生产中': 'warning',
    '待收款': 'danger',
    '已完成': 'success',
    '已取消': 'info'
  }
  return typeMap[status] || 'info'
}

const formatMoney = (amount) => {
  return (amount || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

// 生命周期
onMounted(() => {
  // 恢复视图模式
  const savedViewMode = localStorage.getItem('projectViewMode')
  if (savedViewMode) {
    viewMode.value = savedViewMode
  }
  
  loadProjects()
  loadDesigners()
})
</script>

<style scoped>
.projects-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  margin: 0;
}

.filter-card {
  margin-bottom: 20px;
}

.view-switch {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.project-cards {
  min-height: 400px;
}

.table-card {
  min-height: 400px;
}

.el-pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .view-switch {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .filter-card :deep(.el-form-item) {
    margin-bottom: 12px;
  }
}
</style>