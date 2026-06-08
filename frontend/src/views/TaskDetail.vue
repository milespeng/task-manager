<!--
  页面名称：TaskDetail
  功能描述：任务详情页，展示任务元信息、执行日志，支持实时输出
  日志策略：
    - 任务执行中（pending/running）：先加载已有日志 → 建立 WebSocket 接收增量
    - 任务已结束（success/failed/cancelled）：仅加载历史日志，不建 WebSocket
-->
<template>
  <div class="task-detail-page" v-loading="loading">
    <!-- 返回 + 操作 -->
    <div class="detail-toolbar">
      <el-button @click="$router.back()" :icon="ArrowLeft">返回列表</el-button>
      <div class="toolbar-actions" v-if="task">
        <el-button
          v-if="task.status === 'pending' || task.status === 'running'"
          type="warning"
          @click="handleCancel"
          :loading="cancelling"
        >
          取消任务
        </el-button>
        <el-popconfirm
          v-if="task.status !== 'running'"
          title="确定要删除这条任务记录吗？"
          @confirm="handleDelete"
        >
          <template #reference>
            <el-button type="danger" :loading="deleting">删除记录</el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <!-- 任务信息卡片 -->
    <el-card v-if="task" class="info-card" shadow="never">
      <template #header>
        <div class="info-card-header">
          <span class="info-title">{{ task.name }}</span>
          <el-tag :type="statusType" size="default">{{ statusLabel }}</el-tag>
        </div>
      </template>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="任务 ID">{{ task.id }}</el-descriptions-item>
        <el-descriptions-item label="任务类型">
          <el-tag size="small" :type="task.task_type === 'shell_command' ? '' : 'success'">
            {{ task.task_type === 'shell_command' ? 'Shell 命令' : 'Python 脚本' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">
          {{ task.description || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(task.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="开始时间">
          {{ task.started_at ? formatTime(task.started_at) : '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="结束时间">
          {{ task.finished_at ? formatTime(task.finished_at) : '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="WebSocket">
          <el-tag size="small" :type="wsConnected ? 'success' : 'info'">
            {{ wsConnected ? '已连接' : '未连接' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 日志查看器 -->
    <el-card v-if="task" class="log-card" shadow="never">
      <template #header>
        <div class="log-card-header">
          <span>执行日志</span>
          <el-button size="small" text @click="refreshTask">刷新</el-button>
        </div>
      </template>
      <LogViewer
        ref="logViewerRef"
        :initial-output="task.output"
        :status="task.status"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getTaskDetail,
  cancelTask,
  deleteTask,
  type ITaskDetail,
} from '@/api/tasks'
import { useWebSocket } from '@/composables/useWebSocket'
import LogViewer from '@/components/LogViewer.vue'

const route = useRoute()
const router = useRouter()

// ===== 响应式数据 =====
const task = ref<ITaskDetail | null>(null)
const loading = ref(false)
const cancelling = ref(false)
const deleting = ref(false)
const logViewerRef = ref<InstanceType<typeof LogViewer>>()

// ===== WebSocket =====
const taskId = computed(() => route.params.id as string)
const { message: wsMessage, connected: wsConnected, connect: wsConnect, disconnect: wsDisconnect } = useWebSocket(taskId.value)

/** 监听 WebSocket 消息 */
watch(wsMessage, (msg) => {
  if (!msg || !task.value) return

  if (msg.type === 'output' && msg.data) {
    // 追加实时日志
    logViewerRef.value?.appendText(msg.data)
  }

  if (msg.type === 'status_change') {
    // 更新任务状态
    task.value.status = msg.status as ITaskDetail['status']
    // 终态时自动断开
    if (['success', 'failed', 'cancelled'].includes(msg.status)) {
      wsDisconnect()
    }
  }
})

// ===== 计算属性 =====
const statusType = computed(() => {
  const map: Record<string, string> = {
    pending: 'info', running: 'warning', success: 'success',
    failed: 'danger', cancelled: 'info',
  }
  return map[task.value?.status || ''] || 'info'
})

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '待执行', running: '运行中', success: '成功',
    failed: '失败', cancelled: '已取消',
  }
  return map[task.value?.status || ''] || ''
})

// ===== 方法 =====

/** 加载任务详情 */
async function refreshTask() {
  try {
    task.value = await getTaskDetail(taskId.value)
  } catch {
    router.replace({ name: 'TaskList' })
  }
}

/** 取消任务 */
async function handleCancel() {
  cancelling.value = true
  try {
    await cancelTask(taskId.value)
    ElMessage.success('任务取消请求已提交')
    await refreshTask()
  } finally {
    cancelling.value = false
  }
}

/** 删除任务 */
async function handleDelete() {
  deleting.value = true
  try {
    await deleteTask(taskId.value)
    ElMessage.success('任务已删除')
    router.replace({ name: 'TaskList' })
  } finally {
    deleting.value = false
  }
}

/** 格式化时间 */
function formatTime(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

// ===== 生命周期 =====
onMounted(async () => {
  loading.value = true
  await refreshTask()
  loading.value = false

  // 如果任务仍在执行中，建立 WebSocket 接收实时输出
  if (task.value && ['pending', 'running'].includes(task.value.status)) {
    wsConnect()
  }
})

onUnmounted(() => {
  wsDisconnect()
})
</script>

<style scoped>
.task-detail-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
}

.info-card :deep(.el-card__header) {
  padding: 14px 20px;
}

.info-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-title {
  font-size: 16px;
  font-weight: 600;
}

.log-card :deep(.el-card__header) {
  padding: 10px 20px;
}

.log-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
</style>
