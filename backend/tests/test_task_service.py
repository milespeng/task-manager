"""
测试 task_service.py — 任务业务逻辑层
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreateRequest, TaskTypeEnum
from app.services import task_service


# ── helper ─────────────────────────────────────────────────


def make_create_body(**kwargs) -> TaskCreateRequest:
    defaults = dict(
        name="测试任务",
        description="单元测试用",
        task_type=TaskTypeEnum.shell_command,
        payload="echo hello",
    )
    defaults.update(kwargs)
    return TaskCreateRequest(**defaults)


# ── create_task ────────────────────────────────────────────


class TestCreateTask:
    async def test_basic(self, session: AsyncSession):
        """创建任务应返回 Task 对象，含默认 pending 状态"""
        task = await task_service.create_task(session, make_create_body())
        assert task.id is not None
        assert task.name == "测试任务"
        assert task.status == "pending"
        assert task.task_type == "shell_command"

    async def test_python_script_type(self, session: AsyncSession):
        """创建 Python 脚本任务"""
        task = await task_service.create_task(
            session, make_create_body(task_type=TaskTypeEnum.python_script)
        )
        assert task.task_type == "python_script"

    async def test_persisted(self, session: AsyncSession):
        """任务应写入数据库"""
        task = await task_service.create_task(session, make_create_body())
        result = await session.execute(select(Task).where(Task.id == task.id))
        assert result.scalar_one_or_none() is not None


# ── get_task_by_id ─────────────────────────────────────────


class TestGetTaskById:
    async def test_found(self, session: AsyncSession):
        task = await task_service.create_task(session, make_create_body())
        got = await task_service.get_task_by_id(session, task.id)
        assert got is not None
        assert got.id == task.id

    async def test_not_found(self, session: AsyncSession):
        got = await task_service.get_task_by_id(session, "nonexistent-id")
        assert got is None


# ── get_task_list ──────────────────────────────────────────


class TestGetTaskList:
    async def seed(self, session: AsyncSession, count: int = 5):
        for i in range(count):
            await task_service.create_task(
                session, make_create_body(name=f"任务{i}")
            )

    async def test_empty(self, session: AsyncSession):
        tasks, total = await task_service.get_task_list(session)
        assert tasks == []
        assert total == 0

    async def test_pagination_default(self, session: AsyncSession):
        await self.seed(session, 3)
        tasks, total = await task_service.get_task_list(session)
        assert total == 3
        assert len(tasks) == 3

    async def test_page_size(self, session: AsyncSession):
        await self.seed(session, 10)
        tasks, total = await task_service.get_task_list(session, page=1, page_size=4)
        assert total == 10
        assert len(tasks) == 4

    async def test_status_filter(self, session: AsyncSession):
        await self.seed(session, 5)
        # 默认所有都是 pending，筛选 running 应返回空
        tasks, total = await task_service.get_task_list(
            session, status="running"
        )
        assert tasks == []
        assert total == 0

    async def test_ordered_by_created_at_desc(self, session: AsyncSession):
        await self.seed(session, 3)
        tasks, _ = await task_service.get_task_list(session)
        # 最新创建的在最前
        for i in range(len(tasks) - 1):
            assert tasks[i].created_at >= tasks[i + 1].created_at


# ── update_task_status ─────────────────────────────────────


class TestUpdateTaskStatus:
    async def test_update(self, session: AsyncSession):
        task = await task_service.create_task(session, make_create_body())
        await task_service.update_task_status(session, task.id, "running")
        await session.refresh(task)
        assert task.status == "running"

    async def test_with_extra_fields(self, session: AsyncSession):
        task = await task_service.create_task(session, make_create_body())
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        await task_service.update_task_status(
            session, task.id, "success", output="done", finished_at=now
        )
        await session.refresh(task)
        assert task.status == "success"
        assert task.output == "done"
        assert task.finished_at is not None


# ── delete_task ────────────────────────────────────────────


class TestDeleteTask:
    async def test_delete_existing(self, session: AsyncSession):
        task = await task_service.create_task(session, make_create_body())
        deleted = await task_service.delete_task(session, task.id)
        assert deleted is True
        got = await task_service.get_task_by_id(session, task.id)
        assert got is None

    async def test_delete_not_found(self, session: AsyncSession):
        deleted = await task_service.delete_task(session, "nonexistent")
        assert deleted is False
