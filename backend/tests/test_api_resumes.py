import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models import Application, Vacancy
from tests.factories import make_resume


async def test_создание_и_чтение_резюме(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/resumes",
        json={"name": "Backend Node.js", "raw_text": "Опыт 4 года", "allowed_facts": "Алматы"},
    )

    assert created.status_code == 201
    resume_id = created.json()["id"]

    fetched = await client.get(f"/api/v1/resumes/{resume_id}")

    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Backend Node.js"
    assert fetched.json()["min_score"] == 75


async def test_patch_меняет_только_переданные_поля(client: AsyncClient) -> None:
    resume_id = (
        await client.post("/api/v1/resumes", json={"name": "Go", "allowed_facts": "Астана"})
    ).json()["id"]

    patched = await client.patch(f"/api/v1/resumes/{resume_id}", json={"name": "Go Developer"})

    assert patched.status_code == 200
    assert patched.json()["name"] == "Go Developer"
    assert patched.json()["allowed_facts"] == "Астана"


async def test_архивные_резюме_не_попадают_в_список_по_умолчанию(client: AsyncClient) -> None:
    resume_id = (await client.post("/api/v1/resumes", json={"name": "Старое"})).json()["id"]

    await client.post(f"/api/v1/resumes/{resume_id}/archive")

    assert (await client.get("/api/v1/resumes")).json() == []
    assert len((await client.get("/api/v1/resumes?include_archived=true")).json()) == 1


async def test_дублирование_копирует_текст_и_навыки(client: AsyncClient) -> None:
    resume_id = (
        await client.post("/api/v1/resumes", json={"name": "Backend", "raw_text": "Node.js, Go"})
    ).json()["id"]
    await client.put(
        f"/api/v1/resumes/{resume_id}/skills",
        json={"skills": [{"id": 0, "name": "Go", "is_core": True}]},
    )

    copy = await client.post(f"/api/v1/resumes/{resume_id}/duplicate")

    assert copy.status_code == 200
    assert copy.json()["name"] == "Backend (копия)"
    assert copy.json()["raw_text"] == "Node.js, Go"
    assert [s["name"] for s in copy.json()["skills"]] == ["Go"]


async def test_резюме_с_откликами_нельзя_удалить(
    client: AsyncClient, session: AsyncSession
) -> None:
    resume = make_resume()
    vacancy = Vacancy(hh_id="1", url="https://hh.kz/vacancy/1", title="Backend")
    session.add_all([resume, vacancy])
    await session.flush()
    session.add(Application(vacancy_id=vacancy.id, resume_id=resume.id))
    await session.commit()

    response = await client.delete(f"/api/v1/resumes/{resume.id}")

    assert response.status_code == 409
    assert "архивировать" in response.json()["detail"]["human_message"]


async def test_резюме_без_откликов_удаляется(client: AsyncClient) -> None:
    resume_id = (await client.post("/api/v1/resumes", json={"name": "Черновик"})).json()["id"]

    assert (await client.delete(f"/api/v1/resumes/{resume_id}")).status_code == 204
    assert (await client.get(f"/api/v1/resumes/{resume_id}")).status_code == 404


async def test_правило_компании_проверяется_из_ui(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/company-rules",
        json={"match_type": "CONTAINS", "value": "vash", "action": "SKIP"},
    )

    response = await client.post("/api/v1/company-rules/test", json={"company_name": "ТОО Vash"})

    assert response.status_code == 200
    assert len(response.json()["matched"]) == 1


async def test_вакансии_фильтруются_по_резюме(client: AsyncClient) -> None:
    resume_id = (await client.post("/api/v1/resumes", json={"name": "Backend"})).json()["id"]

    response = await client.get("/api/v1/vacancies", params={"resume_id": resume_id})

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


async def test_бот_без_прогона_отдаёт_состояние_покоя(client: AsyncClient) -> None:
    response = await client.get("/api/v1/bot/status")

    assert response.status_code == 200
    assert response.json()["is_busy"] is False


async def test_запуск_без_входа_в_hh_отклоняется(client: AsyncClient) -> None:
    """Прогон идёт от аккаунта пользователя, поэтому вход проверяется первым.

    Браузер тут не поднимается: тесты не требуют браузера (§30) — проверка
    падает раньше, на неготовой сессии.
    """
    resume_id = (await client.post("/api/v1/resumes", json={"name": "Backend"})).json()["id"]

    response = await client.post(
        "/api/v1/bot/start", json={"resume_id": resume_id, "mode": "MANUAL"}
    )

    assert response.status_code in (400, 409)
    detail = response.json()["detail"]
    assert detail["error_code"] in ("HH_LOGIN_REQUIRED", "BROWSER_NOT_READY", "BROWSER_NOT_STARTED")


async def test_запуск_без_поисковых_профилей_отклоняется(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    resume_id = (await client.post("/api/v1/resumes", json={"name": "Backend"})).json()["id"]

    async def session_ok() -> None:
        return None

    monkeypatch.setattr("app.pipeline.runner.ensure_hh_session", session_ok)

    response = await client.post(
        "/api/v1/bot/start", json={"resume_id": resume_id, "mode": "MANUAL"}
    )

    assert response.status_code == 409
    assert "поисковых профилей" in response.json()["detail"]["human_message"]


async def test_настройки_отдаются_с_дефолтами(client: AsyncClient) -> None:
    response = await client.get("/api/v1/settings")

    data = response.json()
    assert data["limits"]["max_applications_per_day"] == 30
    assert data["delays"]["ranges"]["between_vacancies"] == [3, 8]
    assert data["currency_rates"]["USD"] == 500.0
