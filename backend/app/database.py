"""
数据库引擎与会话管理
使用 SQLAlchemy 2.0 异步引擎 + aiosqlite
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import AsyncAdaptedQueuePool
from .config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=10,
    max_overflow=20,
    connect_args={"check_same_thread": False},
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库表结构"""
    from .models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
