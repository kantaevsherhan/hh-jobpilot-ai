"""Сохранение вакансий и три уровня «уже» (§10)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.browser.extract import VacancyData
from app.browser.search import SearchItem
from app.core.enums import VacancyStatus
from app.storage.models import Application, ResumeVacancy, Vacancy
from app.storage.models.base import utcnow


async def known_hh_ids(session: AsyncSession, hh_ids: list[str]) -> set[str]:
    """Какие из этих вакансий уже в базе.

    Один запрос вместо открытия карточек — на этой отсечке экономится
    основное время повторного прогона.
    """
    if not hh_ids:
        return set()
    rows = await session.scalars(select(Vacancy.hh_id).where(Vacancy.hh_id.in_(hh_ids)))
    return set(rows.all())


async def touch(session: AsyncSession, hh_id: str) -> Vacancy | None:
    """Отметить, что вакансия снова попалась в выдаче."""
    vacancy = await session.scalar(select(Vacancy).where(Vacancy.hh_id == hh_id))
    if vacancy is None:
        return None
    vacancy.last_seen_at = utcnow()
    vacancy.seen_count += 1
    await session.commit()
    return vacancy


async def save_from_search(session: AsyncSession, item: SearchItem) -> tuple[Vacancy, bool]:
    """Строка выдачи → вакансия. Повторный hh_id не создаёт вторую строку."""
    existing = await session.scalar(select(Vacancy).where(Vacancy.hh_id == item.hh_id))
    if existing is not None:
        existing.last_seen_at = utcnow()
        existing.seen_count += 1
        await session.commit()
        return existing, False

    vacancy = Vacancy(
        hh_id=item.hh_id,
        url=item.url,
        title=item.title,
        company_name=item.company_name,
    )
    session.add(vacancy)
    await session.commit()
    await session.refresh(vacancy)
    return vacancy, True


FIELDS_FROM_CARD = (
    "url",
    "title",
    "company_hh_id",
    "company_name",
    "description",
    "description_lang",
    "salary_from",
    "salary_to",
    "currency",
    "salary_gross",
    "work_format",
    "experience",
    "employment",
    "schedule",
    "area",
    "published_at",
    "is_closed",
    "raw_json",
)


async def save_from_card(session: AsyncSession, data: VacancyData) -> tuple[Vacancy, bool]:
    """Данные карточки → вакансия. Существующая обновляется, а не дублируется."""
    vacancy = await session.scalar(select(Vacancy).where(Vacancy.hh_id == data.hh_id))
    is_new = vacancy is None
    if vacancy is None:
        vacancy = Vacancy(hh_id=data.hh_id, url=data.url, title=data.title)
        session.add(vacancy)
    else:
        vacancy.last_seen_at = utcnow()
        vacancy.seen_count += 1

    for field in FIELDS_FROM_CARD:
        value = getattr(data, field)
        if value not in (None, "", {}):
            setattr(vacancy, field, value)

    if data.is_closed and vacancy.closed_detected_at is None:
        vacancy.closed_detected_at = utcnow()

    await session.commit()
    await session.refresh(vacancy)
    return vacancy, is_new


async def get_decision(
    session: AsyncSession, resume_id: int, vacancy_id: int
) -> ResumeVacancy | None:
    """Уже решили? Решение своё на каждое резюме."""
    result: ResumeVacancy | None = await session.scalar(
        select(ResumeVacancy).where(
            ResumeVacancy.resume_id == resume_id,
            ResumeVacancy.vacancy_id == vacancy_id,
        )
    )
    return result


async def ensure_decision(
    session: AsyncSession,
    resume_id: int,
    vacancy_id: int,
    **fields: Any,
) -> ResumeVacancy:
    decision = await get_decision(session, resume_id, vacancy_id)
    if decision is None:
        decision = ResumeVacancy(
            resume_id=resume_id,
            vacancy_id=vacancy_id,
            status=fields.pop("status", VacancyStatus.DISCOVERED.value),
        )
        session.add(decision)
    for field, value in fields.items():
        setattr(decision, field, value)
    await session.commit()
    await session.refresh(decision)
    return decision


async def has_application(session: AsyncSession, vacancy_id: int) -> bool:
    """Уже откликнулись? Проверка глобальная: повторный отклик невозможен
    ни при каких настройках и с любого резюме (§10, §21)."""
    return (
        await session.scalar(select(Application.id).where(Application.vacancy_id == vacancy_id))
    ) is not None


async def rejected_by_model_ids(session: AsyncSession, resume_id: int) -> list[int]:
    """Вакансии, которые отклонила модель, а не фильтры, и на которые не откликались.

    Отсеянные фильтрами (стоп-слова, формат, зарплата) сюда не попадают: при
    повторном анализе фильтры не прогоняются, и они проскочили бы мимо них.
    """
    rows = await session.scalars(
        select(ResumeVacancy.vacancy_id)
        .where(
            ResumeVacancy.resume_id == resume_id,
            ResumeVacancy.status == VacancyStatus.REJECTED_BY_AI.value,
            ResumeVacancy.vacancy_id.not_in(select(Application.vacancy_id)),
        )
        .order_by(ResumeVacancy.vacancy_id)
    )
    return list(rows.all())
