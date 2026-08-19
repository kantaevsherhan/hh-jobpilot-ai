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
