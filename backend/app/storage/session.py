"""Подключение к SQLite и выдача сессий."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.sqlalchemy_url, echo=False, future=True)

SessionMaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def session_factory() -> async_sessionmaker[AsyncSession]:
    """Фабрика сессий для фоновых задач.

    Воркер прогона живёт вне HTTP-запроса, поэтому зависимость FastAPI ему
    не подходит и сессию он открывает сам. Обращение через функцию нужно,
    чтобы тесты могли подменить базу — иначе прогон в тестах пишет в рабочую.
    """
    return SessionMaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """Зависимость FastAPI: сессия на один запрос."""
    async with SessionMaker() as session:
        yield session
