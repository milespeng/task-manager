/**
 * 任务管理 API
 * 功能描述：封装任务相关的所有后端接口调用
 */
import apiClient from './client'

// ===== 类型定义 =====

/** 任务状态 */
export type TaskStatus = 'pending' | 'running' | 'success' | 'failed' | 'cancelled'

/** 任务类型 */
export type TaskType = 'shell_command' | 'python_script'

/** 任务列表项 */
export interface ITaskSummary {
  id: string
  name: string
  task_type: TaskType
  status: TaskStatus
  created_at: string
  started_at: string | null
  finished_at: string | null
}

/** 任务详情（含日志） */
export interface ITaskDetail {
  id: string
  name: string
  description: string | null
  task_type: TaskType
  payload: string
  status: TaskStatus
  output: string
  created_at: string
  updated_at: string
  started_at: string | null
  finished_at: string | null
}

/** 创建任务请求 */
export interface ITaskCreateRequest {
  name: string
  description?: string
  task_type: TaskType
  payload: string
}

/** 分页响应 */
export interface IPaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// ===== 接口方法 =====

/** 获取任务列表 */
export function getTaskList(params: {
  page?: number
  page_size?: number
  status?: TaskStatus
}): Promise<IPaginatedResponse<ITaskSummary>> {
  return apiClient.get('/tasks', { params })
}

/** 创建任务 */
export function createTask(body: ITaskCreateRequest): Promise<ITaskDetail> {
  return apiClient.post('/tasks', body)
}

/** 获取任务详情 */
export function getTaskDetail(id: string): Promise<ITaskDetail> {
  return apiClient.get(`/tasks/${id}`)
}

/** 取消任务 */
export function cancelTask(id: string): Promise<{ message: string }> {
  return apiClient.post(`/tasks/${id}/cancel`)
}

/** 删除任务 */
export function deleteTask(id: string): Promise<{ message: string }> {
  return apiClient.delete(`/tasks/${id}`)
}
