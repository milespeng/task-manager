"""
模块名称：任务数据模型
功能描述：定义任务表的 SQLAlchemy ORM 模型（MySQL）
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Task(Base):
    """任务数据模型，对应 tasks 表"""

    __tablename__ = "tasks"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
        "comment": "任务表",
    }

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="任务唯一标识",
    )

    # 基本信息
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="任务名称"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="任务描述"
    )
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="任务类型: shell_command / python_script"
    )
    payload: Mapped[str] = mapped_column(
        MEDIUMTEXT, nullable=False, comment="任务内容"
    )

    # 状态信息
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="任务状态: pending / running / success / failed / cancelled",
    )
    celery_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Celery 任务 ID"
    )
    output: Mapped[str] = mapped_column(
        MEDIUMTEXT, nullable=False, default="", comment="累计输出日志"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="开始执行时间"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="结束执行时间"
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} name={self.name} status={self.status}>"
