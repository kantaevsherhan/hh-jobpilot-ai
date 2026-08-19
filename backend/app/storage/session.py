"""Подключение к SQLite и выдача сессий."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.sqlalchemy_url, echo=False, future=True)

SessionMaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Зависимость FastAPI: сессия на один запрос."""
    async with SessionMaker() as session:
        yield session
