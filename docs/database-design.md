# 数据库设计

## 概述

- 数据库：MySQL（本地已有环境）
- ORM：SQLAlchemy（异步模式），异步驱动 aiomysql
- 连接配置：通过 `.env` 环境变量管理（不写入代码仓库）

| 环境变量              | 说明           |
|-----------------------|----------------|
| MYSQL_HOST            | 数据库地址，如 localhost |
| MYSQL_PORT            | 数据库端口，默认 3306   |
| MYSQL_USER            | 数据库用户     |
| MYSQL_PASSWORD        | 数据库密码     |
| MYSQL_DATABASE        | 数据库名称     |

### 创建数据库

```sql
-- 请替换为实际数据库名
CREATE DATABASE IF NOT EXISTS <数据库名> CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### MySQL 字段类型映射

| 字段名       | MySQL 类型      | 说明                              |
|-------------|-----------------|-----------------------------------|
| id          | VARCHAR(36)     | UUID 主键                         |
| name        | VARCHAR(255)    | 任务名称                           |
| description | TEXT            | 任务描述                           |
| task_type   | VARCHAR(50)     | 任务类型                           |
| payload     | MEDIUMTEXT      | 任务内容（可能较长）                |
| status      | VARCHAR(20)     | 任务状态                           |
| celery_id   | VARCHAR(100)    | Celery 任务 ID                     |
| output      | MEDIUMTEXT      | 累计输出日志                        |
| created_at  | DATETIME(6)     | 创建时间（微秒精度）                |
| updated_at  | DATETIME(6)     | 最后更新时间                       |
| started_at  | DATETIME(6)     | 开始执行时间                       |
| finished_at | DATETIME(6)     | 结束执行时间                       |

## 索引

| 索引名              | 字段       | 用途               |
|---------------------|------------|--------------------|
| ix_tasks_status     | status     | 按状态过滤查询      |
| ix_tasks_created_at | created_at | 按时间排序          |
| ix_tasks_task_type  | task_type  | 按类型过滤          |

## 状态流转

```
                 ┌──────────┐
                 │  pending  │
                 └────┬─────┘
                      │
                 ┌────▼─────┐
                 │  running  │
                 └────┬─────┘
          ┌───────────┼──────────┐
          │           │          │
    ┌─────▼────┐ ┌───▼────┐ ┌───▼──────────┐
    │ success  │ │ failed │ │  cancelled    │
    └──────────┘ └────────┘ └──────────────┘
```

### 状态说明

| 状态      | 说明                                    | 可转换到                    |
|-----------|-----------------------------------------|----------------------------|
| pending   | 已创建，等待 Celery Worker 领取         | running, cancelled         |
| running   | Worker 正在执行                         | success, failed, cancelled |
| success   | 执行成功完成                            | —（终态）                   |
| failed    | 执行异常退出                            | —（终态）                   |
| cancelled | 用户手动取消（仅 pending/running 可取消）| —（终态）                   |

## DDL 建表语句

```sql
CREATE TABLE tasks (
    id          VARCHAR(36)  NOT NULL PRIMARY KEY COMMENT '任务唯一标识',
    name        VARCHAR(255) NOT NULL              COMMENT '任务名称',
    description TEXT         NULL                  COMMENT '任务描述',
    task_type   VARCHAR(50)  NOT NULL              COMMENT '任务类型',
    payload     MEDIUMTEXT   NOT NULL              COMMENT '任务内容',
    status      VARCHAR(20)  NOT NULL DEFAULT 'pending' COMMENT '任务状态',
    celery_id   VARCHAR(100) NULL                  COMMENT 'Celery 任务 ID',
    output      MEDIUMTEXT   NOT NULL DEFAULT ''   COMMENT '执行输出日志',
    created_at  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    updated_at  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',
    started_at  DATETIME(6)  NULL                  COMMENT '开始执行时间',
    finished_at DATETIME(6)  NULL                  COMMENT '结束执行时间',

    INDEX ix_tasks_status     (status),
    INDEX ix_tasks_created_at (created_at),
    INDEX ix_tasks_task_type  (task_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务表';
```

## SQLAlchemy 模型定义

```python
"""
模块名称：任务数据模型
功能描述：定义任务表的 ORM 模型（MySQL）
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Task(Base):
    """任务数据模型"""

    __tablename__ = "tasks"
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
        "comment": "任务表",
    }

    # 主键
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="任务唯一标识"
    )
    # 基本信息
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="任务名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="任务描述")
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="任务类型")
    payload: Mapped[str] = mapped_column(MEDIUMTEXT, nullable=False, comment="任务内容")
    # 状态信息
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="任务状态"
    )
    celery_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Celery 任务 ID"
    )
    output: Mapped[str] = mapped_column(
        MEDIUMTEXT, nullable=False, default="", comment="执行输出日志"
    )
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, comment="创建时间"
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
```

## 初始化策略

### 开发阶段（首次部署）

使用 Alembic 迁移管理数据库表结构。首次部署执行：

```bash
cd backend
PYTHONPATH=. alembic upgrade head
```

此命令会根据初始迁移创建所有表。

### 已有数据库

如果数据库表已通过 `create_all` 创建，执行以下命令标记基线：

```bash
cd backend
PYTHONPATH=. alembic stamp head
```

### 开发迭代

修改模型后生成新迁移：

```bash
cd backend
PYTHONPATH=. alembic revision --autogenerate -m "变更说明"
PYTHONPATH=. alembic upgrade head
```
