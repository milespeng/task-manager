"""
模块名称：任务业务逻辑
功能描述：封装任务的增删改查业务逻辑，隔离 API 层和数据库操作
"""
from datetime import datetime, timezone

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreateRequest


async def create_task(db: AsyncSession, task_data: TaskCreateRequest) -> Task:
    """
    创建新任务。

    Args:
        db: 数据库会话。
        task_data: 任务创建请求数据。

    Returns:
        Task: 创建成功的任务对象。
    """
    task = Task(
        name=task_data.name,
        description=task_data.description,
        task_type=task_data.task_type.value,
        payload=task_data.payload,
        status="pending",
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def get_task_by_id(db: AsyncSession, task_id: str) -> Task | None:
    """
    根据 ID 获取任务详情。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。

    Returns:
        Task | None: 任务对象，不存在时返回 None。
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def get_task_list(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> tuple[list[Task], int]:
    """
    获取任务列表（分页）。

    Args:
        db: 数据库会话。
        page: 页码，从 1 开始。
        page_size: 每页数量。
        status: 按状态过滤，None 表示不过滤。

    Returns:
        tuple: (任务列表, 总记录数)
    """
    # 构建查询
    query = select(Task)
    count_query = select(func.count(Task.id))

    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)

    # 计算总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(desc(Task.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = list(result.scalars().all())

    return tasks, total


async def update_task_status(
    db: AsyncSession,
    task_id: str,
    status: str,
    **extra_fields,
) -> None:
    """
    更新任务状态。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        status: 新状态。
        **extra_fields: 额外要更新的字段（如 output, finished_at 等）。
    """
    values = {"status": status, "updated_at": datetime.now(timezone.utc), **extra_fields}
    await db.execute(update(Task).where(Task.id == task_id).values(**values))
    await db.flush()


async def delete_task(db: AsyncSession, task_id: str) -> bool:
    """
    删除任务。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。

    Returns:
        bool: 是否删除成功。
    """
    task = await get_task_by_id(db, task_id)
    if task is None:
        return False
    await db.delete(task)
    await db.flush()
    return True
