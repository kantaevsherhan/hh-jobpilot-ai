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


class TestСверенныеСелекторы:
    """Имена data-qa сверены с живой страницей hh.kz.

    Угадывать их нельзя: HH называет узлы не так, как кажется логичным.
    Признак входа искали по «mainmenu_myResumes» — такого узла нет вовсе,
    и вход не определялся, хотя пользователь был авторизован.
    """

    def test_признак_входа_ищет_реальные_узлы(self) -> None:
        assert "mainmenu_profileAndResumes" in HH.LOGGED_IN
        assert "mainmenu_applicantProfilePage" in HH.LOGGED_IN
        # Запасной вариант по ссылкам переживает переименование data-qa
        assert 'a[href^="/applicant/resumes"]' in HH.LOGGED_IN

    def test_занятость_график_и_формат_разные_узлы(self) -> None:
        assert HH.VACANCY_EMPLOYMENT == '[data-qa="common-employment-text"]'
        assert HH.VACANCY_SCHEDULE == '[data-qa="work-schedule-by-days-text"]'
        assert HH.VACANCY_WORK_FORMAT == '[data-qa="work-formats-text"]'

    def test_виджет_вопросов_на_странице_не_путается_с_формой(self) -> None:
        # vacancy-response-question_* — это «Задать вопрос работодателю» на каждой
        # вакансии. Из-за него вакансии ошибочно уходили в «нужны данные»
        assert "vacancy-response-question" not in HH.QUESTION_ITEM
        assert "ответить на несколько вопросов" in HH.QUESTION_ITEM


def test_формат_работы_читается_из_своего_узла() -> None:
    from app.browser.extract import detect_work_format

    assert detect_work_format("Формат работы: удалённо", "График: 5/2") == "REMOTE"
    assert detect_work_format("Формат работы: гибрид", None) == "HYBRID"
    assert detect_work_format("Формат работы: на месте работодателя", None) == "OFFICE"
    assert detect_work_format(None, None) == "UNKNOWN"


def test_лента_рекомендаций_ищет_по_резюме_без_текста() -> None:
    from app.browser.search import build_url

    url = build_url("", resume_hash="4b50d52eff0967434a0039ed1f7a7a43446b35", areas=["160"])

    assert "resume=4b50d52eff0967434a0039ed1f7a7a43446b35" in url
    assert "text=" not in url
    assert "area=160" in url


def test_обычный_поиск_не_меняется() -> None:
    from app.browser.search import build_url

    url = build_url("Vue разработчик")

    assert "text=Vue" in url
    assert "resume=" not in url


def test_идентификатор_резюме_из_ссылки_hh() -> None:
    from app.browser.search import resume_hash_from_url

    url = "https://almaty.hh.kz/resume/4b50d52eff0967434a0039ed1f7a7a43446b35?hhtmFrom=profile"

    assert resume_hash_from_url(url) == "4b50d52eff0967434a0039ed1f7a7a43446b35"
    assert resume_hash_from_url(None) is None
    assert resume_hash_from_url("https://hh.kz/vacancy/123") is None


def test_кнопка_отклика_только_своей_вакансии() -> None:
    # Кнопка с карточки «Вам могут подойти» ведёт на чужую вакансию
    assert "vacancy-serp__vacancy_response" not in HH.APPLY_BUTTON
    assert "vacancy-title-archived-text" in HH.VACANCY_ARCHIVED


async def test_импорт_вакансии_по_чужой_ссылке_отклоняется(client) -> None:
    response = await client.post(
        "/api/v1/vacancies/import", json={"resume_id": 1, "url": "https://hh.kz/resume/abc"}
    )

    assert response.status_code == 409
