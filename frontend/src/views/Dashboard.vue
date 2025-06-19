<template>
  <div class="dashboard-container">
    <!-- 欢迎栏 -->
    <div class="welcome-section">
      <div class="welcome-info">
        <h1>{{ greeting }}，{{ userStore.user?.nickname || userStore.user?.username }}</h1>
        <p>{{ currentDate }} · {{ weatherText }}</p>
      </div>
      <div class="quick-actions">
        <el-button type="primary" icon="Plus" @click="handleCreateProject">
          创建项目
        </el-button>
        <el-button icon="Upload" @click="handleImportProject">
          导入项目
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :xs="24" :sm="12" :md="6" v-for="stat in statistics" :key="stat.title">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" :style="{ backgroundColor: stat.color }">
              <el-icon :size="24">
                <component :is="stat.icon" />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-title">{{ stat.title }}</div>
              <div class="stat-trend" :class="stat.trend > 0 ? 'up' : 'down'">
                <el-icon><component :is="stat.trend > 0 ? 'Top' : 'Bottom'" /></el-icon>
                {{ Math.abs(stat.trend) }}%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 项目进度和任务分布 -->
    <el-row :gutter="20" class="chart-section">
      <el-col :xs="24" :md="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>项目进度</span>
              <el-button link type="primary" @click="router.push('/projects')">
                查看全部
              </el-button>
            </div>
          </template>
          <div class="project-list">
            <div 
              v-for="project in recentProjects" 
              :key="project.id"
              class="project-item"
              @click="handleViewProject(project.id)"
            >
              <div class="project-header">
                <h4>{{ project.name }}</h4>
                <el-tag :type="getStatusType(project.status)" size="small">
                  {{ project.status }}
                </el-tag>
              </div>
              <div class="project-info">
                <span>客户：{{ project.customerName }}</span>
                <span>负责人：{{ project.designerName }}</span>
              </div>
              <el-progress 
                :percentage="project.progress" 
                :status="project.progress === 100 ? 'success' : ''"
              />
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>任务分布</span>
              <el-date-picker
                v-model="taskDateRange"
                type="daterange"
                size="small"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                @change="loadTaskChart"
              />
            </div>
          </template>
          <div ref="taskChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最新动态 -->
    <el-card class="activity-card">
      <template #header>
        <div class="card-header">
          <span>最新动态</span>
          <el-button link type="primary" @click="loadActivities">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      <el-timeline>
        <el-timeline-item
          v-for="activity in activities"
          :key="activity.id"
          :timestamp="formatTime(activity.createdAt)"
          :color="getActivityColor(activity.type)"
        >
          <div class="activity-content">
            <span class="activity-user">{{ activity.userName }}</span>
            <span class="activity-action">{{ activity.action }}</span>
            <span class="activity-target">{{ activity.target }}</span>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'
import { useProjectStore } from '@/stores/project'
import { 
  FolderOpened, 
  List, 
  User, 
  TrendCharts,
  Top,
  Bottom,
  Refresh
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const projectStore = useProjectStore()

// 响应式数据
const taskChartRef = ref()
const taskDateRange = ref([
  dayjs().subtract(7, 'day').format('YYYY-MM-DD'),
  dayjs().format('YYYY-MM-DD')
])
const recentProjects = ref([])
const activities = ref([])

// 计算属性
const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '凌晨好'
  if (hour < 9) return '早上好'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 17) return '下午好'
  if (hour < 19) return '傍晚好'
  return '晚上好'
})

const currentDate = computed(() => {
  return dayjs().format('YYYY年MM月DD日 dddd')
})

const weatherText = computed(() => {
  // 这里可以接入真实的天气API
  return '今日宜：编程'
})

const statistics = computed(() => [
  {
    title: '进行中项目',
    value: projectStore.statistics?.ongoing || 0,
    icon: 'FolderOpened',
    color: '#409EFF',
    trend: 12
  },
  {
    title: '待处理任务',
    value: projectStore.statistics?.pendingTasks || 0,
    icon: 'List',
    color: '#E6A23C',
    trend: -5
  },
  {
    title: '本月完成',
    value: projectStore.statistics?.monthlyCompleted || 0,
    icon: 'TrendCharts',
    color: '#67C23A',
    trend: 8
  },
  {
    title: '团队成员',
    value: userStore.teamCount || 0,
    icon: 'User',
    color: '#909399',
    trend: 0
  }
])

// 图表实例
let taskChart = null

// 方法
const loadDashboardData = async () => {
  try {
    // 加载最近项目
    const projectRes = await projectStore.fetchProjects({
      page: 1,
      pageSize: 5,
      sortBy: 'updated_at',
      sortOrder: 'desc'
    })
    recentProjects.value = projectRes.items

    // 加载最新动态
    await loadActivities()
    
    // 加载统计数据
    await projectStore.fetchStatistics()
  } catch (error) {
    console.error('加载仪表盘数据失败:', error)
  }
}

const loadTaskChart = async () => {
  if (!taskChartRef.value) return
  
  // 初始化图表
  if (!taskChart) {
    taskChart = echarts.init(taskChartRef.value)
  }
  
  // 模拟数据 - 实际应从API获取
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      bottom: 0,
      left: 'center'
    },
    series: [
      {
        name: '任务分布',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: 15, name: '待处理', itemStyle: { color: '#E6A23C' } },
          { value: 25, name: '进行中', itemStyle: { color: '#409EFF' } },
          { value: 8, name: '已完成', itemStyle: { color: '#67C23A' } },
          { value: 3, name: '已延期', itemStyle: { color: '#F56C6C' } }
        ]
      }
    ]
  }
  
  taskChart.setOption(option)
}

const loadActivities = async () => {
  // 模拟数据 - 实际应从API获取
  activities.value = [
    {
      id: 1,
      userName: '张三',
      action: '创建了项目',
      target: '2025春节营销方案',
      type: 'create',
      createdAt: new Date()
    },
    {
      id: 2,
      userName: '李四',
      action: '完成了任务',
      target: 'LOGO设计初稿',
      type: 'complete',
      createdAt: dayjs().subtract(2, 'hour').toDate()
    },
    {
      id: 3,
      userName: '王五',
      action: '更新了项目状态',
      target: '品牌VI设计',
      type: 'update',
      createdAt: dayjs().subtract(5, 'hour').toDate()
    }
  ]
}

const handleCreateProject = () => {
  router.push('/projects/create')
}

const handleImportProject = () => {
  ElMessage.info('导入功能开发中...')
}

const handleViewProject = (id) => {
  router.push(`/projects/${id}`)
}

const getStatusType = (status) => {
  const typeMap = {
    '待报价': 'info',
    '设计中': 'warning',
    '待确认': '',
    '生产中': 'warning',
    '已完成': 'success',
    '已取消': 'danger'
  }
  return typeMap[status] || 'info'
}

const getActivityColor = (type) => {
  const colorMap = {
    create: '#67C23A',
    update: '#409EFF',
    complete: '#67C23A',
    delete: '#F56C6C'
  }
  return colorMap[type] || '#909399'
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

// 生命周期
onMounted(() => {
  loadDashboardData()
  loadTaskChart()
  
  // 响应式处理
  window.addEventListener('resize', () => {
    taskChart?.resize()
  })
})

onBeforeUnmount(() => {
  taskChart?.dispose()
  window.removeEventListener('resize', () => {
    taskChart?.resize()
  })
})
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
}

.welcome-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding: 30px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  color: white;
}

.welcome-info h1 {
  font-size: 28px;
  margin-bottom: 8px;
}

.welcome-info p {
  font-size: 14px;
  opacity: 0.9;
}

.quick-actions {
  display: flex;
  gap: 12px;
}

.stat-cards {
  margin-bottom: 30px;
}

.stat-card {
  transition: transform 0.3s;
}

.stat-card:hover {
  transform: translateY(-5px);
}

.stat-content {
  display: flex;
  align-items: center;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-right: 20px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-trend {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 2px;
}

.stat-trend.up {
  color: #67C23A;
}

.stat-trend.down {
  color: #F56C6C;
}

.chart-section {
  margin-bottom: 30px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.project-item {
  padding: 16px;
  border: 1px solid #EBEEF5;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.project-item:hover {
  border-color: #409EFF;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.project-header h4 {
  margin: 0;
  font-size: 16px;
}

.project-info {
  display: flex;
  gap: 20px;
  margin-bottom: 12px;
  font-size: 14px;
  color: #909399;
}

.activity-card {
  margin-bottom: 30px;
}

.activity-content {
  display: flex;
  gap: 6px;
  font-size: 14px;
}

.activity-user {
  font-weight: 500;
  color: #303133;
}

.activity-action {
  color: #606266;
}

.activity-target {
  color: #409EFF;
  cursor: pointer;
}

.activity-target:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .welcome-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }
  
  .quick-actions {
    width: 100%;
  }
  
  .quick-actions .el-button {
    flex: 1;
  }
}
</style>