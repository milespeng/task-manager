/**
 * API 客户端
 * 功能描述：创建 axios 实例，统一配置 baseURL 和错误处理
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// 响应拦截器：统一提取 data 并处理错误
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default apiClient
