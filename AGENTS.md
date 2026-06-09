# task-manager 项目约定

## Python 版本
- Python 3.14+
- 禁止 `asyncio.get_event_loop()`（Python 3.14 不再自动创建 event loop），改用 `asyncio.run()`

## Celery + async SQLAlchemy
- Celery task 内的 async engine 必须在 `run()` 函数内部创建，不能引用全局 engine
- 每个 task 执行后 `await engine.dispose()` 清理连接池
- 参考 `backend/app/celery_app/tasks.py`

## MySQL
- 已有 Docker 容器 `mysql`（非此项目 docker-compose）
- 端口 3306，root 密码见环境变量
- 示例 .env 见 `backend/.env.example`

## 测试
- 运行：`MYSQL_TEST_PW_FILE=/tmp/.mysql_test_pw PYTHONPATH=. pytest tests/ -v`
- 独立测试数据库 `task_scheduler_test`，function 级 engine 隔离
- 密码通过临时文件传参，不在 .py 中硬编码
- API 测试用 `unittest.mock.patch` mock Celery delay，不依赖 Worker
- 参考 skill: `mysql-async-testing`

## 代码风格
- 注释 / docstring 用中文
- 函数注释用 Google 风格
- Pydantic v2 语法（`model_config` 非 class Config）
- 敏感内容一律走 `.env`，不硬编码

## 前端
- Vue 3 + Composition API + TypeScript
- Element Plus 组件库
- `package-lock.json` 不提交（已加入 `.gitignore`）
- WebSocket 重连用 `intentionalClose` 标记模式（参考 `useWebSocket.ts`）
