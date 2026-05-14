from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, and_
from .models import Base, MediaItem
from contextlib import asynccontextmanager
from typing import AsyncIterator

engine = None
session_factory = None

def init_db(database_url: str):
    global engine, session_factory
    if engine is None:
        engine = create_async_engine(database_url, echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    if session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with session_factory() as session:
        yield session

# Upsert media item: обновляет, если существует vk_id+owner_id, иначе создаёт
async def upsert_media_item(session: AsyncSession, data: dict) -> MediaItem:
    vk_id = data["vk_id"]
    owner_id = data["owner_id"]
    result = await session.execute(
        select(MediaItem).where(and_(MediaItem.vk_id == vk_id, MediaItem.owner_id == owner_id))
    )
    item = result.scalar_one_or_none()
    if item:
        for key, value in data.items():
            setattr(item, key, value)
    else:
        item = MediaItem(**data)
        session.add(item)
    await session.commit()
    return item