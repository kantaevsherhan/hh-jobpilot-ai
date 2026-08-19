from httpx import AsyncClient


async def test_health_отвечает_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_справочники_содержат_русские_подписи(client: AsyncClient) -> None:
    response = await client.get("/api/v1/dictionaries")

    assert response.status_code == 200
    data = response.json()
    assert data["vacancy_status"]["APPLIED"] == "Отклик отправлен"
    assert data["skip_reason"]["SALARY_TOO_LOW"] == "Зарплата ниже минимума"
