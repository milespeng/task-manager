<!--
  页面名称：TaskList
  功能描述：任务列表主页，展示所有任务，支持创建、过滤、查看详情
-->
<template>
  <div class="task-list-page">
    <!-- 顶部操作栏 -->
    <div class="page-toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="statusFilter"
          placeholder="按状态过滤"
          clearable
          style="width: 140px"
          @change="fetchTasks"
        >
          <el-option label="全部" value="" />
          <el-option label="待执行" value="pending" />
          <el-option label="运行中" value="running" />
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
        <el-button @click="fetchTasks" :icon="Refresh">刷新</el-button>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="showCreateDialog = true" :icon="Plus">
          创建任务
        </el-button>
      </div>
    </div>

    <!-- 任务列表 -->
    <div v-loading="loading" class="task-grid">
      <template v-if="tasks.length">
        <TaskCard
          v-for="task in tasks"
          :key="task.id"
          :task="task"
          @click="goToDetail(task.id)"
        />
      </template>
      <el-empty v-else-if="!loading" description="暂无任务，点击上方按钮创建" />
    </div>

    <!-- 分页 -->
    <div class="page-pagination" v-if="total > 0">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchTasks"
      />
    </div>

    <!-- 创建任务弹窗 -->
    <CreateTaskDialog v-model:visible="showCreateDialog" @created="onTaskCreated" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Plus } from '@element-plus/icons-vue'
import { getTaskList, type ITaskSummary, type TaskStatus } from '@/api/tasks'
import TaskCard from '@/components/TaskCard.vue'
import CreateTaskDialog from '@/components/CreateTaskDialog.vue'

const router = useRouter()

// ===== 响应式数据 =====
const tasks = ref<ITaskSummary[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const statusFilter = ref<TaskStatus | ''>('')
const showCreateDialog = ref(false)

// ===== 方法 =====

/** 获取任务列表 */
async function fetchTasks() {
  loading.value = true
  try {
    const res = await getTaskList({
      page: page.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
    })
    tasks.value = res.items
    total.value = res.total
  } catch {
    // 错误由 axios 拦截器处理
  } finally {
    loading.value = false
  }
}

/** 跳转到任务详情 */
function goToDetail(id: string) {
  router.push({ name: 'TaskDetail', params: { id } })
}

/** 创建成功回调 */
function onTaskCreated() {
  page.value = 1
  fetchTasks()
  // 5 秒后自动刷新，等待任务状态变更
  setTimeout(() => fetchTasks(), 5000)
}

// ===== 生命周期 =====
onMounted(() => fetchTasks())
</script>

<style scoped>
.task-list-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  min-height: 200px;
}

.page-pagination {
  display: flex;
  justify-content: center;
}
</style>
