"""Гарантии, которые даёт сама схема, а не код (§10, §21)."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models import Application, Resume, Vacancy


async def test_повторный_hh_id_не_создаёт_вторую_строку(session: AsyncSession) -> None:
    session.add(Vacancy(hh_id="123", url="https://hh.kz/vacancy/123", title="Backend"))
    await session.commit()

    session.add(Vacancy(hh_id="123", url="https://hh.kz/vacancy/123", title="Backend ещё раз"))

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_второй_отклик_на_вакансию_невозможен(session: AsyncSession) -> None:
    resume = Resume(name="Backend Node.js")
    vacancy = Vacancy(hh_id="777", url="https://hh.kz/vacancy/777", title="Go Developer")
    session.add_all([resume, vacancy])
    await session.flush()

    session.add(Application(vacancy_id=vacancy.id, resume_id=resume.id))
    await session.commit()

    session.add(Application(vacancy_id=vacancy.id, resume_id=resume.id))

    with pytest.raises(IntegrityError):
        await session.commit()
