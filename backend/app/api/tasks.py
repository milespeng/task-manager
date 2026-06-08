"""
模块名称：任务管理 API
功能描述：提供任务的增删改查 RESTful 接口
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.task import (
    PaginatedResponse,
    TaskCreateRequest,
    TaskDetailResponse,
    TaskSummaryResponse,
)
from app.services import task_service
from app.celery_app.tasks import (
    execute_shell_command,
    execute_python_script,
    cancel_task as cancel_celery_task,
)

router = APIRouter(prefix="/tasks", tags=["任务管理"])


@router.get(
    "/",
    response_model=PaginatedResponse,
    summary="获取任务列表",
    description="分页查询所有任务，支持按状态过滤。列表中不包含 output 字段以减少传输量。",
)
async def list_tasks(
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页数量")] = 20,
    status: Annotated[str | None, Query(description="按状态过滤")] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> PaginatedResponse:
    """获取任务列表。"""
    tasks, total = await task_service.get_task_list(
        db, page=page, page_size=page_size, status=status
    )
    return PaginatedResponse(
        items=[TaskSummaryResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/",
    response_model=TaskDetailResponse,
    status_code=201,
    summary="创建任务",
    description="创建新任务并提交到 Celery 队列异步执行。",
)
async def create_task(
    body: TaskCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> TaskDetailResponse:
    """创建任务并投递到 Celery。"""
    # 1. 写入数据库
    task = await task_service.create_task(db, body)

    # 2. 投递到 Celery
    if body.task_type.value == "shell_command":
        celery_task = execute_shell_command.delay(str(task.id), body.payload)
    elif body.task_type.value == "python_script":
        celery_task = execute_python_script.delay(str(task.id), body.payload)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的任务类型: {body.task_type.value}")

    # 3. 更新 celery_id
    await task_service.update_task_status(
        db, str(task.id), "pending", celery_id=celery_task.id
    )
    await db.refresh(task)

    return TaskDetailResponse.model_validate(task)


@router.get(
    "/{task_id}",
    response_model=TaskDetailResponse,
    summary="获取任务详情",
    description="获取单个任务的完整信息，包含所有执行输出日志。任务结束后无论间隔多久均可查看历史日志。",
)
async def get_task(
    task_id: str,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> TaskDetailResponse:
    """获取任务详情（含完整输出日志）。"""
    task = await task_service.get_task_by_id(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskDetailResponse.model_validate(task)


@router.post(
    "/{task_id}/cancel",
    summary="取消任务",
    description="取消正在执行或等待中的任务。仅 pending 和 running 状态可取消。",
)
async def cancel_task_endpoint(
    task_id: str,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> dict:
    """取消任务。"""
    task = await task_service.get_task_by_id(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ("pending", "running"):
        raise HTTPException(
            status_code=409,
            detail=f"无法取消状态为 '{task.status}' 的任务，仅 pending 和 running 状态可取消。",
        )

    # 如果有 celery_id，撤销 Celery 任务
    if task.celery_id:
        cancel_celery_task.delay(task_id, task.celery_id)

    # 如果任务还在 pending，直接标记为 cancelled
    if task.status == "pending":
        await task_service.update_task_status(db, task_id, "cancelled")

    return {"message": "任务取消请求已提交"}


@router.delete(
    "/{task_id}",
    summary="删除任务",
    description="删除任务记录。running 状态的任务不可删除，请先取消。",
)
async def delete_task(
    task_id: str,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> dict:
    """删除任务。"""
    task = await task_service.get_task_by_id(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status == "running":
        raise HTTPException(
            status_code=409,
            detail="运行中的任务不可删除，请先取消。",
        )

    await task_service.delete_task(db, task_id)
    return {"message": "任务已删除"}
