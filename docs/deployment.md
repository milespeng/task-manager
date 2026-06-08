# 部署指南

## 环境要求

| 软件        | 最低版本     | 说明                 |
|------------|-------------|----------------------|
| Python     | 3.10+       | 后端运行环境          |
| Node.js    | 18+         | 前端构建与运行        |
| Redis      | 6.0+        | Celery 消息代理（本地已有）|
| MySQL      | 5.7+        | 关系型数据库（本地已有）  |

## 本地开发环境

### 第一步：确认基础服务已启动

确认本地 Redis 和 MySQL 已在运行：

```bash
# 检查 Redis
redis-cli ping
# 应返回 PONG

# 检查 MySQL（按实际用户替换）
mysql -u <用户名> -p -e "SELECT 1"
# 应返回 1
```

### 第二步：确认数据库可用

```bash
# 请替换为实际的用户名、密码和数据库名
mysql -u <用户名> -p<密码> -e "USE <数据库名>; SELECT 1"
# 应返回 1
```

如果数据库或用户尚未创建，执行：

```sql
CREATE DATABASE IF NOT EXISTS <数据库名> CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CREATE USER '<用户名>'@'localhost' IDENTIFIED BY '<密码>';
-- GRANT ALL PRIVILEGES ON <数据库名>.* TO '<用户名>'@'localhost';
-- FLUSH PRIVILEGES;
```

### 第三步：配置环境变量

在 `backend/` 目录下创建 `.env` 文件（**请勿提交到版本控制**）：

```bash
# 后端服务
APP_HOST=0.0.0.0
APP_PORT=8000

# MySQL 连接（按实际环境填写）
MYSQL_HOST=<数据库地址>
MYSQL_PORT=<数据库端口>
MYSQL_USER=<数据库用户>
MYSQL_PASSWORD=<数据库密码>
MYSQL_DATABASE=<数据库名>

# Redis 连接（按实际环境填写）
REDIS_HOST=<Redis 地址>
REDIS_PORT=<Redis 端口>
REDIS_DB=0
```

### 第四步：启动后端

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 启动 FastAPI 服务（首次启动会自动建表）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问：
- API 文档（Swagger）：http://localhost:8000/docs
- API 文档（ReDoc）：http://localhost:8000/redoc

### 第五步：启动 Celery Worker

```bash
# 新开终端窗口
cd backend

# 激活虚拟环境（如果使用）
source venv/bin/activate

# 启动 Worker
celery -A app.celery_app.celery_app worker --loglevel=info --concurrency=4
```

**Worker 参数说明：**

| 参数          | 说明                           |
|--------------|--------------------------------|
| --loglevel   | 日志级别：debug/info/warning/error |
| --concurrency| 并发 Worker 数量，默认 CPU 核数  |

### 第六步：启动前端

```bash
# 新开终端窗口
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

启动后访问：http://localhost:5173

### 第七步：验证

1. 打开浏览器访问 http://localhost:5173
2. 点击「创建任务」按钮，填写任务信息
3. 提交后观察任务状态从「待执行」→「运行中」→「成功」
4. 进入任务详情页，查看实时日志输出

## 一键启动脚本

创建 `start.sh`（macOS/Linux）：

```bash
#!/bin/bash
# 任务调度平台 — 一键启动脚本
# 前提：Redis 和 MySQL 已在本地运行，数据库已创建，.env 已配置

echo "===== 启动后端 ====="
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "===== 启动 Celery Worker ====="
celery -A app.celery_app.celery_app worker --loglevel=info &
CELERY_PID=$!

echo "===== 启动前端 ====="
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "===== 全部启动完成 ====="
echo "前端: http://localhost:5173"
echo "后端: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获退出信号，停止所有进程
trap "kill $BACKEND_PID $CELERY_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
```

```bash
chmod +x start.sh
./start.sh
```

## 生产环境部署

### 后端

```bash
# 使用 Gunicorn + Uvicorn Workers
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Celery Worker 作为系统服务运行
# 推荐使用 supervisor 或 systemd 管理

# supervisor 配置示例 /etc/supervisor/conf.d/task-manager-celery.conf
[program:task-manager-celery]
command=celery -A app.celery_app.celery_app worker --loglevel=info
directory=/opt/task-manager/backend
user=www-data
autostart=true
autorestart=true
```

### 前端

```bash
# 构建静态文件
npm run build

# 将 dist/ 目录部署到 Nginx
# 示例 Nginx 配置
server {
    listen 80;
    server_name task-manager.example.com;

    # 前端静态文件
    root /opt/task-manager/frontend/dist;
    index index.html;

    # Vue Router history 模式
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理到后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 代理
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 常见问题

### 端口被占用

```bash
# 查看占用端口的进程
lsof -i :8000
lsof -i :5173
lsof -i :6379
lsof -i :3306

# 终止进程
kill -9 <PID>
```

### Redis 连接失败

```bash
# 检查 Redis 是否运行
redis-cli ping
# 应返回 PONG

# 检查连接信息
redis-cli info server
```

### MySQL 连接失败

```bash
# 检查 MySQL 是否运行（替换为实际用户名）
mysql -u <用户名> -p -e "SELECT 1"

# 确认数据库已创建
mysql -u <用户名> -p -e "USE <数据库名>; SELECT 1;"

# macOS 通过 brew 启动
brew services start mysql

# Linux 通过 systemd 启动
sudo systemctl start mysql

# 确认 .env 中的连接信息与 MySQL 实际配置一致
```

### Celery Worker 无法启动

```bash
# 检查 Redis 连接
redis-cli ping

# 使用详细日志定位问题
celery -A app.celery_app.celery_app worker --loglevel=debug
```
