/**
 * WebSocket 组合式函数
 * 功能描述：管理与后端 WebSocket 的连接、自动重连、消息接收
 *
 * 重连策略：
 *   - 主动断开（disconnect / 任务结束）→ 不重连
 *   - 被动断开（网络异常 / 服务端关闭）→ 自动重连，最多 5 次，间隔 2s
 *   - 每次成功连接后重置重连计数
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
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempts = 0
  let intentionalClose = false
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
        // 成功连接：重置计数器，清除「主动断开」标记
        reconnectAttempts = 0
        intentionalClose = false
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as IWSMessage
          message.value = data

          // 收到任务结束消息后主动断开（不会再重连）
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
        if (!intentionalClose) {
          attemptReconnect()
        }
      }

      ws.onerror = () => {
        error.value = 'WebSocket 连接异常'
        // onerror 之后必定触发 onclose，由 onclose 负责重连
      }
    } catch {
      error.value = 'WebSocket 连接失败'
      if (!intentionalClose) {
        attemptReconnect()
      }
    }
  }

  /** 主动断开连接（不会触发自动重连） */
  function disconnect() {
    intentionalClose = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      // 移除 onclose/onerror 防止 close 回调中访问已废弃的引用
      ws.onclose = null
      ws.onerror = null
      ws.close()
      ws = null
    }
    connected.value = false
  }

  /** 尝试重连 */
  function attemptReconnect() {
    if (reconnectAttempts >= maxReconnectAttempts) return
    reconnectTimer = setTimeout(() => {
      reconnectAttempts++
      connect()
    }, reconnectDelay)
  }

  /** 组件卸载时清理 */
  function cleanup() {
    disconnect()
  }

  onUnmounted(cleanup)

  return {
    message,
    connected,
    error,
    connect,
    disconnect,
  }
}
