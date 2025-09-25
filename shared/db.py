import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from shared.config import get_settings

settings = get_settings()

# Убеждаемся, что используется aiosqlite для SQLite
database_url = settings.DATABASE_URL
if database_url.startswith('sqlite://') and 'aiosqlite' not in database_url:
    database_url = database_url.replace('sqlite://', 'sqlite+aiosqlite://')

engine = create_async_engine(database_url, future=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def init_db(models_module) -> None:
    async with engine.begin() as conn:
        # create missing tables/columns if not present (SQLite tolerant)
        await conn.run_sync(models_module.Base.metadata.create_all)