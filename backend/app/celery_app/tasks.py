"""
模块名称：Celery 任务定义
功能描述：定义异步执行的任务，支持 Shell 命令和 Python 脚本，实时推送输出到 Redis Pub/Sub
"""
import subprocess
import tempfile
import os
import signal
from datetime import datetime, timezone

import redis
from celery import shared_task
from celery.exceptions import Ignore

from app.celery_app.celery_app import celery_app
from app.config import settings


def get_redis_client():
    """获取 Redis 客户端连接"""
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
    )


def publish_output(task_id: str, output_line: str, status: str = "running"):
    """
    推送输出日志到 Redis Pub/Sub 频道。

    Args:
        task_id: 任务 ID。
        output_line: 输出内容行。
        status: 当前任务状态。
    """
    import json

    client = get_redis_client()
    message = {
        "type": "output",
        "data": output_line,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    client.publish(f"task:{task_id}", json.dumps(message, ensure_ascii=False))


def publish_status_change(task_id: str, status: str):
    """
    推送状态变更消息到 Redis Pub/Sub 频道。

    Args:
        task_id: 任务 ID。
        status: 新状态。
    """
    import json

    client = get_redis_client()
    message = {
        "type": "status_change",
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    client.publish(f"task:{task_id}", json.dumps(message, ensure_ascii=False))


@celery_app.task(bind=True, name="execute_shell_command")
def execute_shell_command(self, task_id: str, command: str):
    """
    执行 Shell 命令并通过 Redis Pub/Sub 实时推送输出。

    Args:
        task_id: 数据库中的任务 ID。
        command: 要执行的 Shell 命令。

    Returns:
        dict: 包含输出和状态的字典。
    """
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from app.models.task import Task

    import asyncio

    async def run():
        # 每个任务内部创建引擎，绑定到当前 asyncio.run() 创建的 event loop
        from app.config import settings

        engine = create_async_engine(
            settings.database_url, echo=False, pool_size=2, max_overflow=5
        )
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        output_lines: list[str] = []
        async with session_factory() as db:
            try:
                # 更新状态为 running
                now = datetime.now(timezone.utc)
                await db.execute(
                    update(Task)
                    .where(Task.id == task_id)
                    .values(
                        status="running",
                        celery_id=self.request.id,
                        started_at=now,
                        updated_at=now,
                    )
                )
                await db.commit()

                publish_status_change(task_id, "running")
                publish_output(task_id, f"$ {command}\n", "running")
                output_lines.append(f"$ {command}\n")

                # 使用 subprocess 执行命令
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    preexec_fn=os.setsid,  # 创建进程组，方便 kill
                )

                # 逐行读取输出
                for line in process.stdout:
                    output_lines.append(line)
                    publish_output(task_id, line, "running")

                process.wait()

                # 判断执行结果
                if process.returncode == 0:
                    status = "success"
                else:
                    status = "failed"
                    output_lines.append(f"\n[进程退出码: {process.returncode}]\n")

                full_output = "".join(output_lines)
                now = datetime.now(timezone.utc)

                await db.execute(
                    update(Task)
                    .where(Task.id == task_id)
                    .values(
                        status=status,
                        output=Task.output + full_output,
                        finished_at=now,
                        updated_at=now,
                    )
                )
                await db.commit()

                publish_status_change(task_id, status)

                return {"status": status, "output": full_output}

            except Exception as exc:
                error_msg = f"\n[错误] {str(exc)}\n"
                output_lines.append(error_msg)
                full_output = "".join(output_lines)
                now = datetime.now(timezone.utc)

                await db.execute(
                    update(Task)
                    .where(Task.id == task_id)
                    .values(
                        status="failed",
                        output=Task.output + full_output,
                        finished_at=now,
                        updated_at=now,
                    )
                )
                await db.commit()

                publish_status_change(task_id, "failed")
                publish_output(task_id, error_msg, "failed")

                raise

        await engine.dispose()

    return asyncio.run(run())


@celery_app.task(bind=True, name="execute_python_script")
def execute_python_script(self, task_id: str, script: str):
    """
    执行 Python 脚本并通过 Redis Pub/Sub 实时推送输出。

    将脚本内容写入临时文件后执行，执行完毕后清理。

    Args:
        task_id: 数据库中的任务 ID。
        script: Python 脚本内容。

    Returns:
        dict: 包含输出和状态的字典。
    """
    # 将脚本写入临时文件
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(script)
        tmp_path = f.name

    try:
        # 复用 Shell 命令执行逻辑
        return execute_shell_command(task_id, f"python3 {tmp_path}")
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@celery_app.task(bind=True, name="cancel_task")
def cancel_task(self, task_id: str, celery_id: str):
    """
    取消正在执行的任务。

    Args:
        task_id: 数据库中的任务 ID。
        celery_id: Celery 任务 ID。

    Returns:
        dict: 操作结果。
    """
    from celery.result import AsyncResult

    # 撤销 Celery 任务
    celery_app.control.revoke(celery_id, terminate=True, signal=signal.SIGTERM)

    # 推送状态变更
    publish_status_change(task_id, "cancelled")
    publish_output(task_id, "\n[任务已被用户取消]\n", "cancelled")

    return {"status": "cancelled", "task_id": task_id}
