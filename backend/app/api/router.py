"""
模块名称：主路由汇总
功能描述：汇总所有子路由，统一注册到 FastAPI 应用
"""
from fastapi import APIRouter

from app.api.tasks import router as tasks_router

# 创建主路由，所有 API 以 /api 为前缀
api_router = APIRouter(prefix="/api")

# 注册子路由
api_router.include_router(tasks_router)
