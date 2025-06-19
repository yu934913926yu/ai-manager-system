<template>
  <el-card 
    class="project-card" 
    :body-style="{ padding: '0' }"
    @click="$emit('click')"
  >
    <!-- 项目头部 -->
    <div class="card-header" :style="{ backgroundColor: statusColor }">
      <div class="header-content">
        <el-tag :type="statusType" effect="dark" size="small">
          {{ project.status }}
        </el-tag>
        <el-dropdown @command="handleCommand" @click.stop>
          <el-button circle size="small" :icon="MoreFilled" />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="edit" :icon="Edit">
                编辑项目
              </el-dropdown-item>
              <el-dropdown-item command="status" :icon="Refresh">
                更新状态
              </el-dropdown-item>
              <el-dropdown-item command="delete" :icon="Delete" divided>
                删除项目
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    
    <!-- 项目内容 -->
    <div class="card-body">
      <h3 class="project-name">{{ project.projectName }}</h3>
      
      <div class="project-info">
        <div class="info-item">
          <el-icon><User /></el-icon>
          <span>{{ project.customerName }}</span>
        </div>
        <div class="info-item">
          <el-icon><UserFilled /></el-icon>
          <span>{{ project.designerName || '未分配' }}</span>
        </div>
        <div class="info-item">
          <el-icon><Calendar /></el-icon>
          <span>{{ formatDate(project.createdAt) }}</span>
        </div>
      </div>
      
      <div class="project-price">
        <span class="price-label">项目金额</span>
        <span class="price-value">¥{{ formatMoney(project.totalPrice) }}</span>
      </div>
      
      <!-- 项目进度 -->
      <div class="project-progress">
        <div class="progress-header">
          <span>项目进度</span>
          <span>{{ project.progress || 0 }}%</span>
        </div>
        <el-progress 
          :percentage="project.progress || 0" 
          :show-text="false"
          :stroke-width="6"
          :color="progressColor"
        />
      </div>
      
      <!-- 标签 -->
      <div v-if="project.tags?.length" class="project-tags">
        <el-tag 
          v-for="tag in project.tags.slice(0, 3)" 
          :key="tag"
          size="small"
          effect="plain"
        >
          {{ tag }}
        </el-tag>
        <el-tag v-if="project.tags.length > 3" size="small" effect="plain">
          +{{ project.tags.length - 3 }}
        </el-tag>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import dayjs from 'dayjs'
import { 
  MoreFilled, 
  Edit, 
  Delete, 
  User, 
  UserFilled,
  Calendar,
  Refresh
} from '@element-plus/icons-vue'

const props = defineProps({
  project: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['click', 'edit', 'delete', 'status-change'])

// 计算属性
const statusType = computed(() => {
  const typeMap = {
    '待报价': 'info',
    '设计中': 'warning',
    '待确认': '',
    '生产中': 'warning',
    '待收款': 'danger',
    '已完成': 'success',
    '已取消': 'info'
  }
  return typeMap[props.project.status] || 'info'
})

const statusColor = computed(() => {
  const colorMap = {
    '待报价': '#909399',
    '设计中': '#E6A23C',
    '待确认': '#409EFF',
    '生产中': '#E6A23C',
    '待收款': '#F56C6C',
    '已完成': '#67C23A',
    '已取消': '#909399'
  }
  return colorMap[props.project.status] || '#909399'
})

const progressColor = computed(() => {
  const progress = props.project.progress || 0
  if (progress < 30) return '#F56C6C'
  if (progress < 70) return '#E6A23C'
  return '#67C23A'
})

// 方法
const handleCommand = (command) => {
  switch (command) {
    case 'edit':
      emit('edit')
      break
    case 'delete':
      emit('delete')
      break
    case 'status':
      handleStatusChange()
      break
  }
}

const handleStatusChange = () => {
  // 这里可以弹出状态选择对话框
  emit('status-change', {
    projectId: props.project.id,
    currentStatus: props.project.status
  })
}

const formatDate = (date) => {
  return dayjs(date).format('MM/DD')
}

const formatMoney = (amount) => {
  return (amount || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
}
</script>

<style scoped>
.project-card {
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 20px;
  overflow: hidden;
}

.project-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.card-header {
  padding: 12px 16px;
  color: white;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content :deep(.el-button) {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
}

.header-content :deep(.el-button:hover) {
  background: rgba(255, 255, 255, 0.3);
}

.card-body {
  padding: 16px;
}

.project-name {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #606266;
}

.info-item .el-icon {
  color: #909399;
}

.project-price {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 16px;
}

.price-label {
  font-size: 14px;
  color: #606266;
}

.price-value {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.project-progress {
  margin-bottom: 16px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}

.project-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

:deep(.el-tag) {
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>