"""Старые подготовленные отклики соблюдают новый удалённый отбор."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.enums import RemoteMode, SkipReason, VacancyStatus
from app.pipeline import steps
from app.pipeline.applying import ApplyGuard
from app.pipeline.context import RunContext
from app.pipeline.delays import Delays
from app.storage.models import ResumeVacancy, Run, SearchProfile
from tests.factories import make_resume, make_vacancy


@pytest.mark.parametrize("work_format", ["OFFICE", "HYBRID", "UNKNOWN", None, "REMOTE"])
async def test_старое_письмо_отправляется_только_на_удалёнку(
    session, monkeypatch, work_format
) -> None:
    resume = make_resume()
    vacancy = make_vacancy(work_format=work_format)
    session.add_all([resume, vacancy])
    await session.flush()
    run = Run(resume_id=resume.id, mode="AUTO", runtime_mode="LIVE", counters_json={})
    profile = SearchProfile(
        resume_id=resume.id, name="Только удалённо", remote_mode=RemoteMode.REMOTE_ONLY
    )
    decision = ResumeVacancy(
        resume_id=resume.id,
        vacancy_id=vacancy.id,
        status=VacancyStatus.APPLY_PREPARED.value,
    )
    session.add_all([run, profile, decision])
    await session.commit()
    ctx = RunContext(resume=resume, profiles=[profile], company_rules=[], delays=Delays())
    monkeypatch.setattr(steps.applying, "check_can_apply", AsyncMock(return_value=ApplyGuard(True)))
    page = AsyncMock(side_effect=RuntimeError("Доход до браузера"))
    monkeypatch.setattr(steps.browser, "page", page)

    if work_format == "REMOTE":
        with pytest.raises(RuntimeError, match="Доход до браузера"):
            await steps.apply(session, run, ctx, {"vacancy_id": vacancy.id})
        page.assert_awaited_once()
    else:
        await steps.apply(session, run, ctx, {"vacancy_id": vacancy.id})
        page.assert_not_awaited()
        saved = await session.scalar(
            select(ResumeVacancy).where(ResumeVacancy.vacancy_id == vacancy.id)
        )
        assert saved.status == VacancyStatus.FILTERED_OUT.value
        assert saved.skip_reason == SkipReason.WORK_FORMAT.value
