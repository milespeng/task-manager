"""
模块名称：WebSocket 连接管理器
功能描述：管理 WebSocket 连接，通过 Redis Pub/Sub 订阅任务日志并实时推送给前端
"""
import asyncio
import json

import redis.asyncio as redis
from fastapi import WebSocket

from app.config import settings


class ConnectionManager:
    """
    WebSocket 连接管理器。
    每个任务 ID 对应一组 WebSocket 连接，通过 Redis Pub/Sub 接收日志并广播。
    """

    def __init__(self):
        # 任务 ID → WebSocket 连接集合
        self._connections: dict[str, set[WebSocket]] = {}
        # Redis 客户端
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        """懒加载 Redis 异步客户端"""
        if self._redis is None:
            self._redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
            )
        return self._redis

    async def connect(self, websocket: WebSocket, task_id: str):
        """
        接受 WebSocket 连接并注册到对应任务频道。

        Args:
            websocket: WebSocket 连接。
            task_id: 要订阅的任务 ID。
        """
        await websocket.accept()
        if task_id not in self._connections:
            self._connections[task_id] = set()
        self._connections[task_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, task_id: str):
        """
        断开 WebSocket 连接并从频道中移除。

        Args:
            websocket: WebSocket 连接。
            task_id: 任务 ID。
        """
        if task_id in self._connections:
            self._connections[task_id].discard(websocket)
            if not self._connections[task_id]:
                del self._connections[task_id]

    async def broadcast_to_task(self, task_id: str, message: str):
        """
        向订阅了指定任务的所有 WebSocket 连接广播消息。

        Args:
            task_id: 任务 ID。
            message: 要广播的消息文本。
        """
        if task_id not in self._connections:
            return
        dead_connections: list[WebSocket] = []
        for ws in self._connections[task_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead_connections.append(ws)
        # 清理断开的连接
        for ws in dead_connections:
            await self.disconnect(ws, task_id)

    async def subscribe_task(self, task_id: str):
        """
        启动后台任务：订阅 Redis Pub/Sub 频道，将消息广播给 WebSocket 客户端。

        该协程作为 FastAPI BackgroundTask 运行。

        Args:
            task_id: 要订阅的任务 ID。
        """
        r = await self._get_redis()
        pubsub = r.pubsub()
        channel = f"task:{task_id}"

        try:
            await pubsub.subscribe(channel)

            # 持续监听消息
            async for message in pubsub.listen():
                if message["type"] == "message":
                    # 转发给所有连接的 WebSocket 客户端
                    await self.broadcast_to_task(task_id, message["data"])

                    # 如果收到状态变更消息且任务已结束，停止监听
                    try:
                        data = json.loads(message["data"])
                        if data.get("type") == "status_change" and data.get("status") in (
                            "success",
                            "failed",
                            "cancelled",
                        ):
                            break
                    except json.JSONDecodeError:
                        pass

        except Exception:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()


# 全局连接管理器单例
manager = ConnectionManager()
