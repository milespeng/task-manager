"""
测试 API 层 — /api/tasks/ 路由
"""
from unittest.mock import ANY, AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.task import TaskCreateRequest, TaskTypeEnum
from app.services import task_service


# ── helper ─────────────────────────────────────────────────


async def create_task_via_service(session, **kwargs) -> dict:
    """通过 service 直接创建任务（绕过 Celery），返回 id"""
    defaults = dict(
        name="API 测试",
        task_type=TaskTypeEnum.shell_command,
        payload="echo test",
    )
    defaults.update(kwargs)
    body = TaskCreateRequest(**defaults)
    task = await task_service.create_task(session, body)
    return {"id": task.id, "status": task.status}


# ── GET /api/tasks/ ────────────────────────────────────────


class TestListTasks:
    async def test_empty_list(self, client: AsyncClient):
        resp = await client.get("/api/tasks/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    async def test_with_tasks(self, client: AsyncClient, session):
        await create_task_via_service(session, name="任务A")
        await create_task_via_service(session, name="任务B")
        resp = await client.get("/api/tasks/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        names = [item["name"] for item in data["items"]]
        assert "任务A" in names
        assert "任务B" in names

    async def test_pagination(self, client: AsyncClient, session):
        for i in range(10):
            await create_task_via_service(session, name=f"任务{i}")
        resp = await client.get("/api/tasks/?page=1&page_size=3")
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["total"] == 10
        assert data["page"] == 1
        assert data["page_size"] == 3

    async def test_status_filter(self, client: AsyncClient, session):
        await create_task_via_service(session, name="待执行")
        resp = await client.get("/api/tasks/?status=running")
        data = resp.json()
        assert data["total"] == 0


# ── POST /api/tasks/ ───────────────────────────────────────


class TestCreateTaskApi:
    @patch("app.api.tasks.execute_shell_command.delay")
    async def test_create_shell(
        self, mock_delay, client: AsyncClient, session
    ):
        mock_delay.return_value.id = "celery-mock-id"
        payload = {
            "name": "新建任务",
            "task_type": "shell_command",
            "payload": "echo hello",
        }
        resp = await client.post("/api/tasks/", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "新建任务"
        assert data["status"] == "pending"

    @patch("app.api.tasks.execute_python_script.delay")
    async def test_create_python(
        self, mock_delay, client: AsyncClient, session
    ):
        mock_delay.return_value.id = "celery-py-id"
        payload = {
            "name": "Python 任务",
            "task_type": "python_script",
            "payload": "print('hi')",
        }
        resp = await client.post("/api/tasks/", json=payload)
        assert resp.status_code == 201

    async def test_create_validation_error(self, client: AsyncClient):
        resp = await client.post("/api/tasks/", json={"name": ""})
        assert resp.status_code == 422  # validation error

    async def test_response_has_all_fields(
        self, client: AsyncClient, session
    ):
        with patch("app.api.tasks.execute_shell_command.delay") as mock:
            mock.return_value.id = "cid"
            payload = {
                "name": "完整字段",
                "task_type": "shell_command",
                "payload": "echo full",
            }
            resp = await client.post("/api/tasks/", json=payload)
            data = resp.json()
            # 应包含 TaskDetailResponse 的所有字段
            for field in [
                "id", "name", "description", "task_type", "payload",
                "status", "output", "created_at", "updated_at",
                "started_at", "finished_at",
            ]:
                assert field in data, f"缺少字段: {field}"


# ── GET /api/tasks/{id} ────────────────────────────────────


class TestGetTaskDetail:
    async def test_found(self, client: AsyncClient, session):
        task_id = (await create_task_via_service(session))["id"]
        resp = await client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

    async def test_not_found(self, client: AsyncClient):
        resp = await client.get("/api/tasks/nonexistent-id")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "任务不存在"


# ── POST /api/tasks/{id}/cancel ────────────────────────────


class TestCancelTask:
    async def test_cancel_pending(self, client: AsyncClient, session):
        task_id = (await create_task_via_service(session))["id"]
        with patch("app.api.tasks.cancel_celery_task.delay"):
            resp = await client.post(f"/api/tasks/{task_id}/cancel")
        assert resp.status_code == 200
        # pending 状态应立即标记为 cancelled
        detail = await task_service.get_task_by_id(session, task_id)
        assert detail.status == "cancelled"

    async def test_cancel_already_failed(self, client: AsyncClient, session):
        task_id = (await create_task_via_service(session))["id"]
        await task_service.update_task_status(session, task_id, "success")
        resp = await client.post(f"/api/tasks/{task_id}/cancel")
        assert resp.status_code == 409
        assert "无法取消" in resp.json()["detail"]

    async def test_cancel_not_found(self, client: AsyncClient):
        resp = await client.post("/api/tasks/nonexistent/cancel")
        assert resp.status_code == 404


# ── DELETE /api/tasks/{id} ─────────────────────────────────


class TestDeleteTaskApi:
    async def test_delete_pending(self, client: AsyncClient, session):
        task_id = (await create_task_via_service(session))["id"]
        resp = await client.delete(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["message"] == "任务已删除"

    async def test_delete_running(self, client: AsyncClient, session):
        task_id = (await create_task_via_service(session))["id"]
        await task_service.update_task_status(session, task_id, "running")
        resp = await client.delete(f"/api/tasks/{task_id}")
        assert resp.status_code == 409
        assert "不可删除" in resp.json()["detail"]

    async def test_delete_not_found(self, client: AsyncClient):
        resp = await client.delete("/api/tasks/nonexistent")
        assert resp.status_code == 404
