"""init task table

Revision ID: 7f590c1d2cad
Revises:
Create Date: 2026-06-09 13:31:25.776108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '7f590c1d2cad'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 tasks 表（基线迁移）"""
    op.create_table(
        "tasks",
        sa.Column("id", mysql.VARCHAR(length=36), nullable=False, comment="任务唯一标识"),
        sa.Column("name", mysql.VARCHAR(length=255), nullable=False, comment="任务名称"),
        sa.Column("description", mysql.TEXT(), nullable=True, comment="任务描述"),
        sa.Column(
            "task_type",
            mysql.VARCHAR(length=50),
            nullable=False,
            comment="任务类型: shell_command / python_script",
        ),
        sa.Column("payload", mysql.MEDIUMTEXT(), nullable=False, comment="任务内容"),
        sa.Column(
            "status",
            mysql.VARCHAR(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment="任务状态: pending / running / success / failed / cancelled",
        ),
        sa.Column(
            "celery_id", mysql.VARCHAR(length=100), nullable=True, comment="Celery 任务 ID"
        ),
        sa.Column("output", mysql.MEDIUMTEXT(), nullable=False, comment="累计输出日志"),
        sa.Column(
            "created_at",
            mysql.DATETIME(),
            nullable=False,
            server_default=sa.func.now(),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            mysql.DATETIME(),
            nullable=False,
            server_default=sa.func.now(),
            comment="更新时间",
        ),
        sa.Column("started_at", mysql.DATETIME(), nullable=True, comment="开始执行时间"),
        sa.Column("finished_at", mysql.DATETIME(), nullable=True, comment="结束执行时间"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_default_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        comment="任务表",
    )
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"])
    op.create_index(op.f("ix_tasks_created_at"), "tasks", ["created_at"])


def downgrade() -> None:
    """删除 tasks 表"""
    op.drop_index(op.f("ix_tasks_created_at"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_status"), table_name="tasks")
    op.drop_table("tasks")
