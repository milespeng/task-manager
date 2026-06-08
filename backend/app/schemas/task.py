"""
模块名称：任务数据结构
功能描述：定义任务的 Pydantic 请求/响应 Schema，用于 API 数据校验和序列化
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ===== 枚举定义 =====

class TaskTypeEnum(str, Enum):
    """任务类型枚举"""
    shell_command = "shell_command"
    python_script = "python_script"


class TaskStatusEnum(str, Enum):
    """任务状态枚举"""
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


# ===== 请求 Schema =====

class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    name: str = Field(
        ..., min_length=1, max_length=255, description="任务名称"
    )
    description: str | None = Field(None, description="任务描述")
    task_type: TaskTypeEnum = Field(..., description="任务类型")
    payload: str = Field(..., min_length=1, description="任务内容（命令或脚本）")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "数据备份",
                "description": "备份 MySQL 数据库",
                "task_type": "shell_command",
                "payload": "echo '开始备份' && sleep 3 && echo '备份完成'",
            }
        }
    }


# ===== 响应 Schema =====

class TaskSummaryResponse(BaseModel):
    """任务列表项（不含 output，减少传输量）"""
    id: str
    name: str
    task_type: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class TaskDetailResponse(BaseModel):
    """任务详情（含完整 output）"""
    id: str
    name: str
    description: str | None = None
    task_type: str
    payload: str
    status: str
    output: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    """分页响应"""
    items: list[TaskSummaryResponse]
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
