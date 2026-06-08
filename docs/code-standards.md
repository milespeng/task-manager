# 代码规范

## 一、Python 后端规范

### 1.1 命名规范

| 类型         | 规范            | 示例                              |
|--------------|-----------------|-----------------------------------|
| 模块/文件    | 小写下划线       | `task_service.py`                 |
| 类名         | 大驼峰           | `TaskService`, `TaskCreateSchema` |
| 函数/方法    | 小写下划线       | `create_task()`, `get_task_by_id()`|
| 变量         | 小写下划线       | `task_id`, `page_size`           |
| 常量         | 大写下划线       | `MAX_PAGE_SIZE`, `DEFAULT_STATUS` |

### 1.2 文件头注释

每个 `.py` 文件顶部必须包含模块文档字符串：

```python
"""
模块名称：{模块名}
功能描述：{简要描述本模块的功能}
"""
```

### 1.3 函数注释

采用 Google 风格文档字符串：

```python
async def create_task(
    db: AsyncSession,
    task_data: TaskCreateSchema
) -> Task:
    """
    创建新任务并投递到 Celery 队列。

    Args:
        db: 数据库会话。
        task_data: 任务创建请求数据。

    Returns:
        Task: 创建成功的任务对象。

    Raises:
        ValueError: 任务类型不支持时抛出。
    """
```

### 1.4 API 路由规范

- 路由前缀统一使用 `/api`
- 每个路由函数必须包含 `summary` 和 `tags`
- 返回类型使用 `response_model` 声明

```python
router = APIRouter(prefix="/api/tasks", tags=["任务管理"])

@router.post(
    "/",
    response_model=TaskResponseSchema,
    summary="创建任务",
    description="创建一个新任务并提交到 Celery 队列异步执行"
)
async def create_task(
    body: TaskCreateSchema,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TaskResponseSchema:
    """创建新任务。"""
    ...
```

### 1.5 异步规范

- 数据库操作使用 `AsyncSession`
- 外部 IO 操作使用异步库
- Celery 调用使用 `delay()` 或 `apply_async()`（同步调用，不阻塞事件循环）

```python
# 正确：await 异步数据库操作
task = await task_service.create_task(db, task_data)

# 正确：Celery 调用是同步的，不阻塞
celery_task = execute_task.delay(task.id)
```

### 1.6 导入顺序

```python
# 1. 标准库
import uuid
from datetime import datetime

# 2. 第三方库
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# 3. 本地模块
from app.database import get_db
from app.models.task import Task
```

---

## 二、Vue / TypeScript 前端规范

### 2.1 命名规范

| 类型         | 规范            | 示例                              |
|--------------|-----------------|-----------------------------------|
| 组件文件     | 大驼峰           | `TaskList.vue`, `LogViewer.vue`   |
| 组合式函数   | camelCase + use  | `useWebSocket.ts`                 |
| 路由路径     | kebab-case       | `/task-detail/:id`                |
| 接口/类型    | I 前缀 + 大驼峰  | `ITask`, `ITaskCreateRequest`     |
| 变量/函数    | camelCase        | `taskList`, `fetchTasks()`        |
| 常量         | UPPER_SNAKE      | `DEFAULT_PAGE_SIZE`               |

### 2.2 组件结构

每个 `.vue` 文件遵循统一的区域划分：

```vue
<!--
  组件名称：TaskList
  功能描述：任务列表页面，展示所有任务及其状态
-->
<template>
  <!-- 模板内容 -->
</template>

<script setup lang="ts">
// ===== 导入 =====
import { ref, onMounted } from 'vue'

// ===== 类型定义 =====
interface ITask {
  id: string
  name: string
  status: string
}

// ===== 响应式数据 =====
const tasks = ref<ITask[]>([])
const loading = ref(false)

// ===== 计算属性 =====

// ===== 方法 =====
async function fetchTasks() {
  loading.value = true
  // ...
  loading.value = false
}

// ===== 生命周期 =====
onMounted(() => fetchTasks())
</script>

<style scoped>
/* 组件样式 */
</style>
```

### 2.3 API 调用规范

统一使用 axios 实例，集中管理：

```typescript
// api/client.ts —— 创建 axios 实例
import axios from 'axios'

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000,
})

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API 请求失败:', error)
    return Promise.reject(error)
  }
)
```

```typescript
// api/tasks.ts —— 按模块封装接口
import { apiClient } from './client'
import type { ITask, ITaskCreateRequest, IPageParams, IPageResponse } from '@/types'

/** 获取任务列表 */
export async function getTaskList(params: IPageParams): Promise<IPageResponse<ITask>> {
  return await apiClient.get('/tasks', { params })
}

/** 创建任务 */
export async function createTask(body: ITaskCreateRequest): Promise<ITask> {
  return await apiClient.post('/tasks', body)
}

/** 获取任务详情 */
export async function getTaskDetail(id: string): Promise<ITask> {
  return await apiClient.get(`/tasks/${id}`)
}

/** 取消任务 */
export async function cancelTask(id: string): Promise<void> {
  return await apiClient.post(`/tasks/${id}/cancel`)
}

/** 删除任务 */
export async function deleteTask(id: string): Promise<void> {
  return await apiClient.delete(`/tasks/${id}`)
}
```

### 2.4 类型定义

集中管理类型定义：

```typescript
// types/index.ts

/** 任务状态枚举 */
export type TaskStatus = 'pending' | 'running' | 'success' | 'failed' | 'cancelled'

/** 任务类型枚举 */
export type TaskType = 'shell_command' | 'python_script'

/** 任务列表项 */
export interface ITask {
  id: string
  name: string
  description?: string
  task_type: TaskType
  payload: string
  status: TaskStatus
  output: string
  created_at: string
  updated_at: string
  started_at?: string
  finished_at?: string
}

/** 创建任务请求 */
export interface ITaskCreateRequest {
  name: string
  description?: string
  task_type: TaskType
  payload: string
}

/** 分页参数 */
export interface IPageParams {
  page: number
  page_size: number
  status?: TaskStatus
}

/** 分页响应 */
export interface IPageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
```

---

## 三、Git 提交规范

### 3.1 提交格式

```
<类型>(<范围>): <简要描述>

类型：
  feat     - 新功能
  fix      - 修复 Bug
  docs     - 文档更新
  style    - 代码格式调整（不影响功能）
  refactor - 代码重构
  test     - 测试相关
  chore    - 构建、依赖、工具变更

范围：
  backend  - 后端
  frontend - 前端
  docs     - 文档
  infra    - 基础设施

示例：
  feat(backend): 添加任务创建接口
  feat(frontend): 实现任务列表页面
  fix(ws): 修复 WebSocket 断线重连问题
  docs: 添加 API 接口文档
  chore(infra): 添加 docker-compose 配置
```

### 3.2 分支管理

- `main` — 主分支，保持稳定
- `dev` — 开发分支
- `feat/xxx` — 功能开发分支
- `fix/xxx` — Bug 修复分支

---

## 四、通用规范

### 4.1 中文使用原则

| 场景           | 使用语言 | 说明                     |
|----------------|----------|--------------------------|
| 注释           | 中文     | 方便团队成员理解          |
| 文档字符串      | 中文     | 模块/类/函数说明         |
| API 接口描述    | 中文     | summary, description, tags |
| 用户界面文案    | 中文     | 按钮、标签、提示信息      |
| 变量/函数名    | 英文     | 编程语言惯例              |
| 类名/文件名     | 英文     | 编程语言惯例              |
| Git 提交信息    | 中英均可  | 描述清晰即可              |

### 4.2 错误处理

后端统一异常响应结构，前端统一 toaster 提示：

```python
# 后端：自定义异常
class TaskNotFoundError(HTTPException):
    def __init__(self, task_id: str):
        super().__init__(
            status_code=404,
            detail=f"任务不存在: {task_id}"
        )
```

```typescript
// 前端：统一错误提示
import { ElMessage } from 'element-plus'

function handleError(error: unknown): void {
  const message = error instanceof Error ? error.message : '操作失败'
  ElMessage.error(message)
}
```
