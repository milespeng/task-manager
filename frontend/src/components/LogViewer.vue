<!--
  组件名称：LogViewer
  功能描述：终端风格的日志查看器，支持实时追加和静态展示
-->
<template>
  <div class="log-viewer" ref="containerRef">
    <div class="log-header">
      <span class="log-header-dot" :class="statusColor"></span>
      <span class="log-header-text">{{ statusText }}</span>
      <span class="log-header-hint" v-if="!lines.length">等待输出...</span>
    </div>
    <div class="log-body" ref="bodyRef">
      <pre v-if="lines.length" class="log-content"><code><span
        v-for="(line, i) in lines"
        :key="i"
      >{{ line }}</span></code></pre>
      <div v-else class="log-empty">暂无输出</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue'

const props = defineProps<{
  /** 初始日志内容（从 API 获取的历史日志） */
  initialOutput?: string
  /** 任务状态 */
  status?: string
}>()

const containerRef = ref<HTMLElement>()
const bodyRef = ref<HTMLElement>()

/** 日志行列表 */
const lines = ref<string[]>([])

/** 追加一行日志 */
function appendLine(line: string) {
  lines.value.push(line)
  scrollToBottom()
}

/** 追加原始文本（自动按换行拆分） */
function appendText(text: string) {
  if (!text) return
  const parts = text.split('\n')
  for (let i = 0; i < parts.length - 1; i++) {
    lines.value.push(parts[i] + '\n')
  }
  const last = parts[parts.length - 1]
  if (last) {
    lines.value.push(last)
  }
  scrollToBottom()
}

/** 滚动到底部 */
function scrollToBottom() {
  nextTick(() => {
    if (bodyRef.value) {
      bodyRef.value.scrollTop = bodyRef.value.scrollHeight
    }
  })
}

/** 状态指示颜色 */
const statusColor = computed(() => {
  const map: Record<string, string> = {
    pending: 'dot-gray',
    running: 'dot-green',
    success: 'dot-green',
    failed: 'dot-red',
    cancelled: 'dot-gray',
  }
  return map[props.status || ''] || 'dot-gray'
})

/** 状态文字 */
const statusText = computed(() => {
  const map: Record<string, string> = {
    pending: '待执行',
    running: '执行中',
    success: '已完成',
    failed: '执行失败',
    cancelled: '已取消',
  }
  return map[props.status || ''] || props.status || '未知'
})

/** 加载初始日志 */
watch(
  () => props.initialOutput,
  (output) => {
    if (output) {
      appendText(output)
    }
  },
  { immediate: true }
)

/** 状态变为终态时自动滚动到底部 */
watch(
  () => props.status,
  () => {
    scrollToBottom()
  }
)

defineExpose({ appendLine, appendText, scrollToBottom })
</script>

<style scoped>
.log-viewer {
  border-radius: 8px;
  overflow: hidden;
  background: #1e1e1e;
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
}

.log-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #2d2d2d;
  border-bottom: 1px solid #3c3c3c;
}

.log-header-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot-green {
  background: #4caf50;
}

.dot-red {
  background: #f44336;
}

.dot-gray {
  background: #9e9e9e;
}

.log-header-text {
  font-size: 13px;
  color: #ccc;
}

.log-header-hint {
  font-size: 12px;
  color: #888;
  margin-left: auto;
}

.log-body {
  max-height: 500px;
  overflow-y: auto;
  padding: 12px 16px;
}

.log-body::-webkit-scrollbar {
  width: 6px;
}

.log-body::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 3px;
}

.log-content {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-content code {
  font-family: inherit;
}

.log-empty {
  color: #666;
  font-size: 13px;
  text-align: center;
  padding: 20px 0;
}
</style>
