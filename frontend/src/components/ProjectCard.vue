<template>
  <el-card 
    :class="['project-card', { 'is-selected': selected }]"
    @click="handleClick"
  >
    <template #header>
      <div class="card-header">
        <div class="project-title">
          <span class="project-number">{{ project.projectNumber }}</span>
          <el-tag :type="getStatusType(project.status)" size="small">
            {{ project.status }}
          </el-tag>
        </div>
        <el-dropdown @command="handleCommand" @click.stop>
          <el-button :icon="MoreFilled" link />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="view">查看详情</el-dropdown-item>
              <el-dropdown-item command="edit">编辑</el-dropdown-item>
              <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </template>
    
    <div class="project-info">
      <div class="info-row">
        <el-icon><User /></el-icon>
        <span class="label">客户：</span>
        <span class="value">{{ project.customerName }}</span>
      </div>
      
      <div class="info-row">
        <el-icon><Document /></el-icon>
        <span class="label">项目：</span>
        <span class="value">{{ project.projectName }}</span>
      </div>
      
      <div class="info-row" v-if="project.totalPrice">
        <el-icon><Money /></el-icon>
        <span class="label">金额：</span>
        <span class="value">¥{{ formatMoney(project.totalPrice) }}</span>
      </div>
      
      <div class="info-row" v-if="project.deadline">
        <el-icon><Calendar /></el-icon>
        <span class="label">截止：</span>
        <span class="value">{{ formatDate(project.deadline) }}</span>
      </div>
      
      <div class="info-row">
        <el-icon><Avatar /></el-icon>
        <span class="label">负责人：</span>
        <span class="value">{{ project.designerName || '未分配' }}</span>
      </div>
    </div>
    
    <div class="card-footer">
      <span class="create-time">
        创建于 {{ formatDate(project.createdAt) }}
      </span>
      <div class="progress-info" v-if="project.progress">
        <el-progress 
          :percentage="project.progress" 
          :stroke-width="6"
          :show-text="false"
        />
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { MoreFilled, User, Document, Money, Calendar, Avatar } from '@element-plus/icons-vue'
import { formatMoney, formatDate } from '@/utils'

const props = defineProps({
  project: {
    type: Object,
    required: true
  },
  selected: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click', 'view', 'edit', 'delete'])

const handleClick = () => {
  emit('click', props.project)
}

const handleCommand = (command) => {
  emit(command, props.project)
}

const getStatusType = (status) => {
  const typeMap = {
    '待报价': 'info',
    '已报价': '',
    '设计中': 'warning',
    '生产中': 'warning',
    '待收款': 'danger',
    '已完成': 'success',
    '已归档': 'info'
  }
  return typeMap[status] || 'info'
}
</script>

<style scoped>
.project-card {
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 16px;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.project-card.is-selected {
  border-color: var(--el-color-primary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.project-number {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.project-info {
  padding: 8px 0;
}

.info-row {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.info-row .el-icon {
  margin-right: 6px;
  color: var(--el-text-color-secondary);
}

.info-row .label {
  margin-right: 4px;
}

.info-row .value {
  color: var(--el-text-color-primary);
  font-weight: 500;
}

.card-footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.create-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.progress-info {
  margin-top: 8px;
}

@media (max-width: 768px) {
  .project-card {
    margin-bottom: 12px;
  }
}
</style>