from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base


@pytest.fixture(scope="session")
def sqlite_url() -> str:
    return "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session(sqlite_url: str) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(sqlite_url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def redis_mock():
    class RedisMock:
        def __init__(self):
            self.messages: list[tuple[str, str]] = []

        async def publish(self, channel: str, payload: str):
            self.messages.append((channel, payload))

    return RedisMock()


@pytest.fixture
def s3_mock(monkeypatch):
    storage: dict[tuple[str, str], bytes] = {}

    class S3Mock:
        def put_object(self, Bucket, Key, Body, ContentType=None):
            _ = ContentType
            storage[(Bucket, Key)] = Body if isinstance(Body, bytes) else Body.read()

        def get_object(self, Bucket, Key):
            from io import BytesIO

            return {"Body": BytesIO(storage[(Bucket, Key)])}

    mock = S3Mock()
    monkeypatch.setattr("app.dependencies.get_s3_client", lambda: mock)
    return mock
