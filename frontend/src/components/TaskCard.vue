<!--
  组件名称：TaskCard
  功能描述：单条任务信息卡片，显示名称、类型、状态和时间
-->
<template>
  <div class="task-card" @click="$emit('click')">
    <div class="task-card-header">
      <span class="task-name">{{ task.name }}</span>
      <el-tag :type="statusType" size="small">{{ statusLabel }}</el-tag>
    </div>
    <div class="task-card-body">
      <span class="task-type">
        <el-icon :size="14"><component :is="typeIcon" /></el-icon>
        {{ typeLabel }}
      </span>
      <span class="task-time">{{ formatTime(task.created_at) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Monitor, Operation } from '@element-plus/icons-vue'
import type { ITaskSummary } from '@/api/tasks'

const props = defineProps<{
  task: ITaskSummary
}>()

defineEmits<{
  click: []
}>()

/** 状态标签颜色 */
const statusType = computed(() => {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return map[props.task.status] || 'info'
})

/** 状态中文标签 */
const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '待执行',
    running: '运行中',
    success: '成功',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[props.task.status] || props.task.status
})

/** 类型图标 */
const typeIcon = computed(() => {
  return props.task.task_type === 'shell_command' ? Monitor : Operation
})

/** 类型中文标签 */
const typeLabel = computed(() => {
  return props.task.task_type === 'shell_command' ? 'Shell 命令' : 'Python 脚本'
})

/** 格式化时间 */
function formatTime(iso: string): string {
  const date = new Date(iso)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${date.getMonth() + 1}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}
</script>

<style scoped>
.task-card {
  padding: 16px 20px;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
  border: 1px solid #ebeef5;
}

.task-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.task-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.task-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.task-card-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #909399;
}

.task-type {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
