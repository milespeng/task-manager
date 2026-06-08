"""
模块名称：数据库引擎
功能描述：创建异步 SQLAlchemy 引擎和会话工厂，提供依赖注入函数
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=False,  # 生产环境改为 False，开发调试可设为 True
    pool_size=10,
    max_overflow=20,
)

# 创建异步会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """ORM 模型基类"""


async def get_db() -> AsyncSession:
    """
    获取数据库会话（FastAPI 依赖注入）。

    示例:
        @router.get("/tasks")
        async def list_tasks(db: Annotated[AsyncSession, Depends(get_db)]):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
