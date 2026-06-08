/**
 * WebSocket 组合式函数
 * 功能描述：管理与后端 WebSocket 的连接、自动重连、消息接收
 */
import { ref, onUnmounted } from 'vue'

/** WebSocket 消息类型 */
export interface IWSMessage {
  type: 'output' | 'status_change'
  data?: string
  status: string
  timestamp: string
}

export function useWebSocket(taskId: string) {
  const message = ref<IWSMessage | null>(null)
  const connected = ref(false)
  const error = ref<string | null>(null)

  let ws: WebSocket | null = null
  let reconnectTimer: number | null = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 5
  const reconnectDelay = 2000

  /** 获取 WebSocket URL */
  function getWsUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/tasks/${taskId}`
  }

  /** 建立连接 */
  function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    try {
      ws = new WebSocket(getWsUrl())

      ws.onopen = () => {
        connected.value = true
        error.value = null
        reconnectAttempts = 0
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as IWSMessage
          message.value = data

          // 收到任务结束消息后关闭连接
          if (
            data.type === 'status_change' &&
            ['success', 'failed', 'cancelled'].includes(data.status)
          ) {
            disconnect()
          }
        } catch {
          // 忽略解析错误
        }
      }

      ws.onclose = () => {
        connected.value = false
        ws = null
        // 自动重连
        attemptReconnect()
      }

      ws.onerror = () => {
        error.value = 'WebSocket 连接异常'
      }
    } catch {
      error.value = 'WebSocket 连接失败'
      attemptReconnect()
    }
  }

  /** 断开连接 */
  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    reconnectAttempts = maxReconnectAttempts // 阻止自动重连
    if (ws) {
      ws.close()
      ws = null
    }
    connected.value = false
  }

  /** 尝试重连 */
  function attemptReconnect() {
    if (reconnectAttempts >= maxReconnectAttempts) return
    reconnectTimer = window.setTimeout(() => {
      reconnectAttempts++
      connect()
    }, reconnectDelay)
  }

  /** 清理 */
  function cleanup() {
    disconnect()
  }

  // 组件卸载时自动清理
  onUnmounted(cleanup)

  return {
    message,
    connected,
    error,
    connect,
    disconnect,
  }
}
