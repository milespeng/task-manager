# 系统架构

## 整体架构图

```
┌──────────────────┐       WebSocket        ┌──────────────────┐
│   Vue 3 前端      │◄──────────────────────►│   FastAPI 后端    │
│   端口: 5173      │       REST API         │   端口: 8000      │
└──────────────────┘◄──────────────────────►└────────┬─────────┘
                                                     │
                                    ┌─────────────────┼─────────────────┐
                                    │                 │                 │
                              ┌─────▼─────┐    ┌──────▼─────────┐  ┌───▼──────────┐
                              │   Redis    │    │     MySQL       │  │    Celery    │
                              │  (本地)    │    │    (本地)       │  │   Worker     │
                              │ Broker +   │    │  持久化存储     │  │  任务执行器   │
                              │ Pub/Sub    │    │  端口: 3306     │  │              │
                              │ 端口: 6379 │    └────────────────┘  └──────────────┘
                              └────────────┘
```

## 核心数据流

### 实时 + 持久化双通道设计

系统采用"实时推送 + 持久化存储"双通道机制，确保任务日志在执行中和执行后均可查看：

```
                    任务执行中（实时通道）       任务结束后（持久化通道）
                    ─────────────────────       ──────────────────────
                     WebSocket + Redis           REST API + MySQL
                     推送实时日志                 返回完整历史日志
```

**设计要点：**

- **执行中**：Celery Worker 每行输出同时写入两条路径 —— Redis Pub/Sub（实时推送前端）和数据库 output 字段（持久化）
- **执行后**：日志已完整保存在数据库，无论间隔多久（24 小时、7 天或更久），通过 `GET /api/tasks/{id}` 即可获取全部输出
- **无过期**：日志数据存储在 MySQL 的 `tasks.output` 字段中，只要未删除任务记录即可永久查看

### 任务创建与执行流程

```
用户创建任务 → FastAPI 写入数据库 → 投递 Celery 任务
                                         │
Celery Worker 领取任务 → 逐行执行 ──┬──→ Redis Pub/Sub → WebSocket → 前端实时展示
                                    │
                                    └──→ 追加写入 DB.tasks.output（持久化）
                                         │
任务结束 → 更新 status + finished_at → 日志永久可查（GET /api/tasks/{id}）
```

### 详细时序

```
前端              FastAPI             Redis           Celery Worker        MySQL
 │                   │                  │                   │                │
 │── POST /api/tasks─►│                  │                   │                │
 │                   │─────────────────────────────────────────────────────►│ 写入任务
 │                   │── apply_async ──►│                   │                │
 │◄── 201 Created ───│                  │                   │                │
 │                   │                  │── 投递任务 ──────►│                │
 │── WS /ws/tasks/id─►│                 │                   │                │
 │                   │── SUBSCRIBE ────►│                   │                │
 │                   │                  │◄── PUBLISH ───────│                │
 │◄── {"type":"output","data":"..."} ──│                   │                │
 │                   │                  │                   │── 追加 output ►│ 持久化
 │                   │                  │◄── PUBLISH ───────│                │
 │◄── {"type":"output","data":"..."} ──│                   │── 追加 output ►│ 持久化
 │                   │                  │◄── PUBLISH done ──│                │
 │◄── {"type":"status_change","status":"success"} ──│      │                │
 │                   │─────────────────────────────────────────────────────►│ 更新状态
 │                   │                  │                   │                │
 │  ═══════════════ 24 小时后 ═══════════════════════════                  │
 │                   │                  │                   │                │
 │── GET /api/tasks/id────────────────────────────────────────────────────►│ 读取 output
 │◄── 200 { output: "完整日志..." } ──│                   │                │
```

### 前端日志展示策略

```
进入任务详情页
    │
    ├── 任务状态是 pending 或 running？
    │       │
    │       ├── 1. 先请求 GET /api/tasks/{id} 获取已有输出，渲染到 LogViewer
    │       └── 2. 建立 WebSocket 连接 /ws/tasks/{id}，接收增量日志
    │              WebSocket 收到 output → 追加到 LogViewer 末尾
    │              收到 status_change → 刷新状态显示，关闭 WebSocket
    │
    └── 任务状态是 success / failed / cancelled？
            │
            └── 仅请求 GET /api/tasks/{id}，返回完整历史日志
               直接渲染到 LogViewer（不需要 WebSocket）
```

## 项目目录结构

```
task-manager/
├── README.md                         # 项目说明
├── .gitignore                        # 全局 Git 忽略规则
├── docs/                             # 项目文档
│   ├── architecture.md               # 系统架构
│   ├── api-design.md                 # 接口设计
│   ├── database-design.md            # 数据库设计
│   ├── code-standards.md             # 代码规范
│   └── deployment.md                 # 部署指南
├── backend/                          # 后端项目根目录
│   ├── .env                          # 环境变量配置（含敏感信息，不提交）
│   ├── .env.example                  # 环境变量配置模板（可提交）
│   ├── .gitignore                    # 后端 Git 忽略规则
│   ├── requirements.txt              # Python 依赖清单
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI 入口，生命周期管理，WebSocket 路由
│   │   ├── config.py                 # 配置管理（Pydantic Settings，读取 .env）
│   │   ├── database.py               # 异步数据库引擎与会话工厂
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── task.py               # 任务数据模型（SQLAlchemy ORM）
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── task.py               # 请求/响应数据结构（Pydantic）
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # 主路由汇总
│   │   │   └── tasks.py              # 任务 CRUD 接口（增删改查）
│   │   ├── ws/
│   │   │   ├── __init__.py
│   │   │   └── manager.py            # WebSocket 连接管理器（Redis Pub/Sub 订阅）
│   │   ├── celery_app/
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py         # Celery 应用配置（Redis Broker）
│   │   │   └── tasks.py              # Celery 任务定义（Shell/Python 执行器）
│   │   └── services/
│   │       ├── __init__.py
│   │       └── task_service.py       # 任务业务逻辑层
├── frontend/                         # 前端项目根目录
│   ├── .gitignore                    # 前端 Git 忽略规则
│   ├── index.html                    # HTML 入口
│   ├── package.json                  # 依赖与脚本
│   ├── vite.config.ts                # Vite 构建配置（含 API/WS 代理）
│   ├── tsconfig.json                 # TypeScript 配置
│   ├── tsconfig.node.json            # Node 端 TypeScript 配置
│   ├── src/
│   │   ├── main.ts                   # Vue 应用入口（注册 Element Plus、Router）
│   │   ├── App.vue                   # 根组件（全局布局）
│   │   ├── router/
│   │   │   └── index.ts              # 路由配置（/ 和 /task/:id）
│   │   ├── api/
│   │   │   ├── client.ts             # Axios 实例（baseURL、拦截器）
│   │   │   └── tasks.ts              # 任务 API 封装 + TypeScript 类型定义
│   │   ├── composables/
│   │   │   └── useWebSocket.ts       # WebSocket 组合式函数（自动重连）
│   │   ├── views/
│   │   │   ├── TaskList.vue          # 任务列表页（分页、过滤、创建）
│   │   │   └── TaskDetail.vue        # 任务详情页（信息卡片+实时日志）
│   │   ├── components/
│   │   │   ├── TaskCard.vue          # 任务卡片组件
│   │   │   ├── CreateTaskDialog.vue  # 创建任务弹窗
│   │   │   └── LogViewer.vue         # 终端风格日志查看器
│   │   └── env.d.ts                  # 环境类型声明
```

## 技术选型说明

| 决策项       | 选择             | 理由                                              |
|-------------|------------------|---------------------------------------------------|
| 数据库       | MySQL（本地已有） | 生产级关系型数据库，异步驱动 aiomysql，通过环境变量配置连接 |
| UI 组件库    | Element Plus     | Vue 3 生态最成熟的企业级组件库，中文社区活跃         |
| 实时通信     | Redis Pub/Sub    | 轻量级消息推送，无需额外 WebSocket 服务器           |
| ORM         | SQLAlchemy 异步  | FastAPI 原生异步支持，性能更优                      |
| 前端构建     | Vite             | 极速冷启动和 HMR，Vue 官方推荐                      |
| 前端语言     | TypeScript       | 类型安全，更好的 IDE 支持和可维护性                  |
