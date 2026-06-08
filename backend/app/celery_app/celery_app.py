"""
模块名称：Celery 应用配置
功能描述：创建并配置 Celery 实例，连接 Redis 作为 Broker 和 Result Backend
"""
from celery import Celery

from app.config import settings

# 创建 Celery 应用
celery_app = Celery(
    "task_manager",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.celery_app.tasks"],  # 自动发现任务模块
)

# Celery 配置
celery_app.conf.update(
    # 任务序列化格式
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务结果过期时间（秒），7 天
    result_expires=604800,
    # 任务确认模式：任务执行完成后确认
    task_acks_late=True,
    # Worker 预取数量
    worker_prefetch_multiplier=1,
    # 任务追踪：任务开始执行时标记为 STARTED
    task_track_started=True,
    # 结果后端连接配置
    result_backend_transport_options={
        "master_name": "mymaster",
    },
)
