"""Состояние браузера без его запуска.

Playwright тут не поднимается: тесты не требуют браузера (§30).
"""

from httpx import AsyncClient

from app.browser.manager import BrowserManager, BrowserState
from app.browser.selectors import HH


async def test_незапущенный_браузер_отдаёт_понятный_статус(client: AsyncClient) -> None:
    response = await client.get("/api/v1/browser/status")

    assert response.status_code == 200
    assert response.json()["state"] == BrowserState.STOPPED
    assert response.json()["label"] == "Не запущен"
    assert response.json()["is_running"] is False


async def test_проверка_входа_без_браузера_не_падает() -> None:
    manager = BrowserManager()

    state = await manager.check_auth()

    assert state == BrowserState.STOPPED


def test_профиль_разворачивается_в_абсолютный_путь() -> None:
    manager = BrowserManager()

    assert manager.user_data_dir.is_absolute()
    # Живая сессия HH обязана лежать в data/, которая целиком в .gitignore (§29)
    assert "data" in manager.user_data_dir.parts


def test_селекторы_собраны_в_одном_месте() -> None:
    # Ни одного page.locator со строкой вне этого модуля быть не должно (§33 п.7)
    assert HH.BASE_URL == "https://hh.kz"
    assert "data-qa" in HH.LOGGED_IN
    assert "data-qa" in HH.APPLY_BUTTON
