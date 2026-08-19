"""Общие фикстуры тестов.

Тесты не требуют ни браузера, ни Ollama, ни интернета:
база — SQLite в памяти, HTTP идёт напрямую в ASGI-приложение.
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
