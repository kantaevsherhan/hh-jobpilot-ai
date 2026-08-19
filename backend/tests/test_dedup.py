"""Дедупликация и три уровня «уже» (§10, §30)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.browser.extract import VacancyData, detect_language
from app.browser.search import SearchItem
from app.storage.models import Application, Vacancy
from app.storage.repositories import vacancies as repo
from tests.factories import make_resume

ITEM = SearchItem(
    hh_id="100500",
    url="https://hh.kz/vacancy/100500",
    title="Backend Developer",
    company_name="ТОО ABC",
)


async def test_повторный_hh_id_не_создаёт_вторую_строку(session: AsyncSession) -> None:
    first, is_new_first = await repo.save_from_search(session, ITEM)
    second, is_new_second = await repo.save_from_search(session, ITEM)

    total = await session.scalar(select(func.count()).select_from(Vacancy))
    assert total == 1
    assert first.id == second.id
    assert is_new_first is True
    assert is_new_second is False


async def test_повторная_встреча_увеличивает_счётчик(session: AsyncSession) -> None:
    await repo.save_from_search(session, ITEM)
    vacancy, _ = await repo.save_from_search(session, ITEM)

    assert vacancy.seen_count == 2


async def test_известные_id_возвращаются_одним_запросом(session: AsyncSession) -> None:
    await repo.save_from_search(session, ITEM)

    known = await repo.known_hh_ids(session, ["100500", "999", "777"])

    assert known == {"100500"}


async def test_карточка_дополняет_строку_из_выдачи(session: AsyncSession) -> None:
    vacancy, _ = await repo.save_from_search(session, ITEM)

    data = VacancyData(
        hh_id="100500",
        url=ITEM.url,
        title="Backend Developer",
        description="Полное описание вакансии",
        salary_from=700_000,
        currency="KZT",
    )
    updated, is_new = await repo.save_from_card(session, data)

    total = await session.scalar(select(func.count()).select_from(Vacancy))
    assert total == 1
    assert is_new is False
    assert updated.id == vacancy.id
    assert updated.salary_from == 700_000


async def test_решения_разных_резюме_не_видят_друг_друга(session: AsyncSession) -> None:
    backend, go = make_resume(name="Backend"), make_resume(name="Go")
    session.add_all([backend, go])
    vacancy, _ = await repo.save_from_search(session, ITEM)
    await session.flush()

    await repo.ensure_decision(session, backend.id, vacancy.id, status="APPLIED", score=90)
    await repo.ensure_decision(session, go.id, vacancy.id, status="FILTERED_OUT", score=20)

    backend_decision = await repo.get_decision(session, backend.id, vacancy.id)
    go_decision = await repo.get_decision(session, go.id, vacancy.id)

    assert backend_decision is not None
    assert go_decision is not None
    assert backend_decision.status == "APPLIED"
    assert go_decision.status == "FILTERED_OUT"


async def test_отклик_виден_глобально_а_не_по_резюме(session: AsyncSession) -> None:
    backend, go = make_resume(name="Backend"), make_resume(name="Go")
    session.add_all([backend, go])
    vacancy, _ = await repo.save_from_search(session, ITEM)
    await session.flush()
    session.add(Application(vacancy_id=vacancy.id, resume_id=backend.id))
    await session.commit()

    # Отклик отправлен с одного резюме, но повторный запрещён с любого
    assert await repo.has_application(session, vacancy.id) is True


class TestЯзыкОписания:
    def test_русский(self) -> None:
        assert detect_language("Требуется разработчик на Node.js в команду") == "ru"

    def test_казахский_по_специфическим_буквам(self) -> None:
        assert detect_language("Бағдарламашы қажет, тәжірибе үш жыл") == "kk"

    def test_английский(self) -> None:
        assert detect_language("We are looking for a backend developer") == "en"

    def test_пустое_описание_считается_русским(self) -> None:
        assert detect_language("") == "ru"
