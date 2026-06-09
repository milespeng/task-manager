# API 接口设计

## 基础信息

- 基础路径：`http://localhost:8000/api`
- 响应格式：JSON
- 字符编码：UTF-8

## 通用响应结构

所有 API 接口直接返回 JSON 数据体（无额外包裹层）：

### 成功响应

直接返回对象或数组，HTTP 状态码表示操作结果：

| 状态码 | 说明                          |
|--------|-------------------------------|
| 200    | 请求成功                       |
| 201    | 创建成功                       |
| 400    | 请求参数错误                   |
| 404    | 任务不存在                     |
| 409    | 任务状态冲突（如重复取消）      |
| 500    | 服务器内部错误                 |

### 错误响应

```json
{
  "detail": "错误描述信息"
}
```

- 4xx 错误：`detail` 字段包含人类可读的错误信息
- 5xx 错误：生产环境可能隐藏具体错误细节

## RESTful 接口

### 1. 获取任务列表

```
GET /api/tasks
```

**查询参数：**

| 参数       | 类型    | 默认值 | 说明       |
|-----------|---------|--------|------------|
| page      | integer | 1      | 页码       |
| page_size | integer | 20     | 每页数量   |
| status    | string  | —      | 按状态过滤 |

**成功响应：**

```json
{
  "items": [
    {
      "id": "a1b2c3d4-...",
      "name": "数据备份任务",
      "task_type": "shell_command",
      "status": "success",
      "created_at": "2026-06-08T10:00:00",
      "started_at": "2026-06-08T10:00:01",
      "finished_at": "2026-06-08T10:00:15"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### 2. 创建任务

```
POST /api/tasks
```

**请求体：**

```json
{
  "name": "数据备份任务",
  "description": "备份 MySQL 数据库到 /backup 目录",
  "task_type": "shell_command",
  "payload": "mysqldump -u root mydb > /backup/mydb.sql"
}
```

**字段说明：**

| 字段        | 类型   | 必填 | 说明                                    |
|------------|--------|------|-----------------------------------------|
| name       | string | 是   | 任务名称，最大 255 字符                   |
| description| string | 否   | 任务描述                                 |
| task_type  | string | 是   | 任务类型：shell_command / python_script  |
| payload    | string | 是   | 任务内容（Shell 命令 或 Python 代码）     |

**成功响应（201 Created）：**

```json
{
  "id": "a1b2c3d4-...",
  "name": "数据备份任务",
  "description": null,
  "task_type": "shell_command",
  "payload": "mysqldump -u root mydb > /backup/mydb.sql",
  "status": "pending",
  "output": "",
  "created_at": "2026-06-08T10:00:00",
  "updated_at": "2026-06-08T10:00:00",
  "started_at": null,
  "finished_at": null
}
```

### 3. 获取任务详情（含完整历史日志）

```
GET /api/tasks/{id}
```

> **核心能力：** 此接口始终返回 `output` 字段中的完整执行日志。日志数据持久化存储在数据库中，任务结束后无论间隔多久（24 小时、7 天甚至更久），只要未删除任务记录即可随时查看。

**成功响应：**

```json
{
  "id": "a1b2c3d4-...",
  "name": "数据备份任务",
  "description": "备份 MySQL 数据库到 /backup 目录",
  "task_type": "shell_command",
  "payload": "mysqldump -u root mydb > /backup/mydb.sql",
  "status": "success",
  "output": "-- 开始备份...\n-- 备份完成，文件大小 128MB\n",
  "created_at": "2026-06-08T10:00:00",
  "updated_at": "2026-06-08T10:00:15",
  "started_at": "2026-06-08T10:00:01",
  "finished_at": "2026-06-08T10:00:15"
}
```

**前端使用场景：**

| 场景                   | 调用方式                                              |
|------------------------|-------------------------------------------------------|
| 任务执行中（查看进度）  | 先调此接口获取已有输出，再建立 WebSocket 接收增量日志  |
| 任务已结束（事后回看）  | 仅调此接口即可获取完整历史日志，无需 WebSocket         |
| 任务列表（概览）        | 调 `GET /api/tasks` 列表接口，不含 output 字段以减少传输量 |


### 4. 取消任务

```
POST /api/tasks/{id}/cancel
```

**成功响应：**

```json
{
  "message": "任务取消请求已提交"
}
```

### 5. 删除任务

```
DELETE /api/tasks/{id}
```

**成功响应：**

```json
{
  "message": "任务已删除"
}
```

## WebSocket 接口

### 连接

```
ws://localhost:8000/ws/tasks/{id}
```

连接后在任务执行期间持续接收消息，无需发送任何内容。

### 消息格式

**日志输出消息：**

```json
{
  "type": "output",
  "data": "$ python backup.py\n",
  "status": "running",
  "timestamp": "2026-06-08T12:00:00"
}
```

**状态变更消息：**

```json
{
  "type": "status_change",
  "status": "success",
  "timestamp": "2026-06-08T12:00:05"
}
```

**消息字段说明：**

| 字段      | 类型   | 说明                                     |
|----------|--------|------------------------------------------|
| type     | string | 消息类型：output / status_change         |
| data     | string | 日志内容（仅 output 类型）                |
| status   | string | 当前状态：running / success / failed      |
| timestamp| string | ISO 8601 格式时间戳                       |

### 连接行为

- 客户端连接后立即开始接收消息
- 无需发送任何请求，服务端主动推送
- 如果任务已结束，服务端发送当前状态后关闭连接
- 支持断线重连（前端 useWebSocket 自动处理）
- **WebSocket 仅用于实时推送，不替代持久化存储**：连接断开或任务结束后的历史日志通过 `GET /api/tasks/{id}` 获取

### 实时 + 回看协作机制

```
任务 running 中：
  前端 WebSocket 连接 ──► 实时接收日志输出行
  同时请求 GET /api/tasks/{id} ──► 获取从开始到当前的已有输出
  两者合并渲染到 LogViewer

任务已结束（success/failed/cancelled）：
  前端仅请求 GET /api/tasks/{id} ──► 获取完整历史输出
  无需建立 WebSocket 连接
```
