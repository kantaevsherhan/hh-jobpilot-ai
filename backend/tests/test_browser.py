"""Состояние браузера без его запуска.

Playwright тут не поднимается: тесты не требуют браузера (§30).
"""

import pytest
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


async def test_закрытое_окно_переводит_состояние_в_не_запущен() -> None:
    """Пользователь вправе закрыть окно руками в любой момент.

    До этого менеджер продолжал считать браузер живым и выдавал
    «проверьте интернет» вместо «браузер не запущен».
    """
    manager = BrowserManager()
    manager.state = BrowserState.READY

    manager._on_context_closed()

    assert manager.state == BrowserState.STOPPED
    assert manager.is_running is False
    assert (await manager.status())["label"] == "Не запущен"


async def test_обращение_к_странице_закрытого_браузера_даёт_понятную_ошибку() -> None:
    from app.core.errors import AppError

    manager = BrowserManager()

    with pytest.raises(AppError) as exc:
        await manager.page()

    assert exc.value.error_code == "BROWSER_NOT_STARTED"
    assert "Настройки" in exc.value.human_message


async def test_прогон_не_стартует_без_входа_в_hh(monkeypatch: pytest.MonkeyPatch) -> None:
    """Бот работает от аккаунта пользователя и входит только вручную (§9).

    Без активной сессии запускать прогон бессмысленно: выдача и карточки
    открываются от его имени.
    """
    from app.core.errors import ConflictError
    from app.pipeline import runner

    manager = BrowserManager()
    manager.state = BrowserState.NEEDS_LOGIN

    async def fake_check() -> BrowserState:
        return BrowserState.NEEDS_LOGIN

    monkeypatch.setattr(manager, "check_auth", fake_check)
    monkeypatch.setattr(manager, "_context", object())
    monkeypatch.setattr("app.browser.manager.browser", manager)

    with pytest.raises(ConflictError) as exc:
        await runner.ensure_hh_session()

    assert exc.value.error_code == "HH_LOGIN_REQUIRED"
    assert "hh.kz" in exc.value.human_message


async def test_при_активной_сессии_прогон_не_блокируется(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.pipeline import runner

    manager = BrowserManager()

    async def fake_check() -> BrowserState:
        return BrowserState.READY

    monkeypatch.setattr(manager, "check_auth", fake_check)
    monkeypatch.setattr(manager, "_context", object())
    monkeypatch.setattr("app.browser.manager.browser", manager)

    await runner.ensure_hh_session()
