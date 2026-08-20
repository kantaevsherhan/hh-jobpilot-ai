"""Общие фикстуры тестов.

Тесты не требуют ни браузера, ни Ollama, ни интернета: база — SQLite
в памяти, HTTP идёт напрямую в ASGI-приложение без сокета.
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.storage import session as session_module
from app.storage.models import Base
from app.storage.session import get_session


def _always(session: AsyncSession) -> Any:
    """Фабрика, всегда отдающая одну и ту же тестовую сессию.

    Закрывать её на выходе из `async with` нельзя — она нужна остальным
    проверкам того же теста.
    """

    class _Ctx:
        async def __aenter__(self) -> AsyncSession:
            return session

        async def __aexit__(self, *_: object) -> None:
            return None

    class _Maker:
        def __call__(self) -> Any:
            return _Ctx()

    return _Maker()


@pytest.fixture
async def session(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncSession]:
    # StaticPool держит одно соединение: у sqlite в памяти база живёт
    # ровно столько, сколько живёт соединение
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as db_session:
        # Воркер прогона открывает сессии сам, вне HTTP-запроса. Без подмены
        # фабрики тесты бота писали бы в рабочую базу разработчика
        monkeypatch.setattr(session_module, "session_factory", lambda: _always(db_session))
        yield db_session

    await engine.dispose()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _session_override() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _session_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _clean_browser_state() -> Any:
    """Менеджер браузера — синглтон на процесс.

    Без сброса состояние, выставленное одним тестом, протекает в следующий.
    """
    from app.browser.manager import BrowserState, browser

    browser.state = BrowserState.STOPPED
    browser.last_error = None
    yield
    browser.state = BrowserState.STOPPED
    browser.last_error = None
