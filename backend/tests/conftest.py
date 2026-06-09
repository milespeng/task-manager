"""
conftest.py - test fixtures
"""
import os
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from app.database import Base, get_db
from app.main import app


def _build_url() -> str:
    pw_file = os.environ.get("MYSQL_TEST_PW_FILE", "/tmp/.mysql_test_pw")
    try:
        with open(pw_file) as f:
            pw = f.read().strip()
    except (FileNotFoundError, IOError):
        pw = "SET_ME"
    host = os.environ.get("MYSQL_TEST_HOST", "localhost")
    port = os.environ.get("MYSQL_TEST_PORT", "3306")
    db = os.environ.get("MYSQL_TEST_DATABASE", "task_scheduler_test")
    col = chr(58)
    at = chr(64)
    sl = chr(47)
    return "".join([
        "mysql+aiomysql://app_user", col, pw, at,
        host, col, port, sl, db,
    ])


@pytest_asyncio.fixture
async def engine():
    url = _build_url()
    engine = create_async_engine(url, echo=False, pool_size=1)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    async with async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )() as s:
        yield s


@pytest_asyncio.fixture
async def client(session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
