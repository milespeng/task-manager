# 任务调度平台

基于 **FastAPI + Vue 3 + Celery + Redis** 构建的轻量级任务调度平台，支持任务的创建、调度、实时日志查看和执行状态追踪。

## 技术栈

| 层级       | 技术                        | 说明                     |
|------------|-----------------------------|--------------------------|
| 后端框架   | FastAPI                     | Python 异步 Web 框架      |
| 异步任务   | Celery                      | 分布式任务队列            |
| 消息代理   | Redis                       | Celery Broker + 结果存储  |
| 数据库     | SQLite（MVP）/ PostgreSQL   | 可通过 SQLAlchemy 切换    |
| 前端框架   | Vue 3 + Composition API     | 响应式 UI 框架            |
| 构建工具   | Vite                        | 前端构建与热更新          |
| UI 组件库  | Element Plus                | 企业级 Vue 3 组件库       |
| 实时通信   | WebSocket + Redis Pub/Sub   | 任务日志实时推送          |

## 核心功能

- **任务管理** — 创建、查看、取消、删除任务
- **任务调度** — 通过 Celery 异步执行，支持 shell 命令和 Python 脚本
- **实时日志** — WebSocket 推送任务执行输出，前端终端风格展示
- **状态追踪** — 任务状态流转：待执行 → 运行中 → 成功/失败/已取消

## 快速开始

```bash
# 1. 启动 Redis
docker-compose up -d redis

# 2. 启动后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. 启动 Celery Worker（新终端）
cd backend
celery -A app.celery_app.celery_app worker --loglevel=info

# 4. 启动前端（新终端）
cd frontend
npm install
npm run dev
```

- 前端地址：http://localhost:5173
- 后端 API 文档：http://localhost:8000/docs

## 文档索引

| 文档                                                | 说明               |
|-----------------------------------------------------|--------------------|
| [系统架构](./docs/architecture.md)                   | 架构设计与数据流    |
| [API 接口设计](./docs/api-design.md)                 | RESTful + WebSocket 接口 |
| [数据库设计](./docs/database-design.md)              | 数据模型与状态流转  |
| [代码规范](./docs/code-standards.md)                 | Python / Vue / Git 规范 |
| [部署指南](./docs/deployment.md)                     | 环境要求与启动步骤  |

## 后续扩展

- [ ] 定时任务（Cron 表达式调度）
- [ ] 任务重试机制
- [ ] 用户认证与权限
- [ ] PostgreSQL 迁移
- [ ] 任务编排（DAG 工作流）
- [ ] 邮件/钉钉通知
- [ ] 任务执行统计看板
- [ ] Docker 容器化部署
