"""
模块名称：FastAPI 应用入口
功能描述：创建 FastAPI 实例，注册路由、WebSocket、CORS 中间件，管理生命周期事件
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.api.router import api_router
from app.ws.manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理。
    启动时：创建数据库表。
    关闭时：释放数据库引擎连接。
    """
    # 启动时执行
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 继续运行
    yield
    # 关闭时执行
    await engine.dispose()


# 创建 FastAPI 应用
app = FastAPI(
    title="任务调度平台",
    description="基于 FastAPI + Celery + Redis 的轻量级任务调度平台",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 跨域配置（开发环境允许前端 5173 端口访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router)


@app.get("/", summary="健康检查", tags=["系统"])
async def health_check():
    """健康检查接口，返回服务运行状态。"""
    return {
        "status": "ok",
        "service": "任务调度平台",
        "version": "1.0.0",
    }


# ===== WebSocket 路由 =====

@app.websocket("/ws/tasks/{task_id}")
async def websocket_task_logs(websocket: WebSocket, task_id: str):
    """
    WebSocket 端点：订阅任务实时日志输出。

    客户端连接到 ws://localhost:8000/ws/tasks/{task_id}
    无需发送任何消息，服务端主动推送：
      - { "type": "output", "data": "...", "status": "running", "timestamp": "..." }
      - { "type": "status_change", "status": "success", "timestamp": "..." }

    任务已结束后，连接仍可建立但会立即收到最终状态并关闭。
    """
    await manager.connect(websocket, task_id)
    try:
        # 启动 Redis 订阅，持续推送消息给客户端
        await manager.subscribe_task(task_id)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await manager.disconnect(websocket, task_id)
