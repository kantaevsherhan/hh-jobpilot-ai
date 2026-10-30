from unittest.mock import AsyncMock

import pytest

from app.core.enums import RemoteMode, SkipReason, VacancyStatus
from app.filters.region import is_kazakhstan
from app.pipeline import steps
from app.pipeline.applying import ApplyGuard
from app.pipeline.context import RunContext
from app.pipeline.delays import Delays
from app.storage.models import ResumeVacancy, Run, SearchProfile
from tests.factories import make_resume, make_vacancy


@pytest.mark.parametrize(
    ("area", "raw", "expected"),
    [
        ("Алматы", {"area": {"id": "160"}}, True),
        ("Астана", {"area": {"id": "159"}}, True),
        ("Алматы", {"area": {"id": "1"}}, False),
        ("Алматы", {"area": {"id": "unknown"}}, False),
        ("Алматы, улица Абая", None, True),
        ("Казахстан", None, True),
        ("Москва", None, False),
        (None, None, False),
    ],
)
def test_country_evidence(area, raw, expected):
    assert is_kazakhstan(area, raw) is expected


@pytest.mark.parametrize("area,allowed", [("Алматы", True), ("Москва", False), (None, False)])
async def test_prepared_application_obeys_country(session, monkeypatch, area, allowed):
    resume = make_resume()
    vacancy = make_vacancy(area=area, work_format="REMOTE")
    session.add_all([resume, vacancy])
    await session.flush()
    run = Run(resume_id=resume.id, mode="AUTO", runtime_mode="LIVE", counters_json={})
    profile = SearchProfile(
        resume_id=resume.id, name="Казахстан", areas=["40"], remote_mode=RemoteMode.REMOTE_ONLY
    )
    decision = ResumeVacancy(
        resume_id=resume.id, vacancy_id=vacancy.id, status=VacancyStatus.APPLY_PREPARED.value
    )
    session.add_all([run, profile, decision])
    await session.commit()
    ctx = RunContext(resume=resume, profiles=[profile], company_rules=[], delays=Delays())
    monkeypatch.setattr(steps.applying, "check_can_apply", AsyncMock(return_value=ApplyGuard(True)))
    page = AsyncMock(side_effect=RuntimeError("browser reached"))
    monkeypatch.setattr(steps.browser, "page", page)
    if allowed:
        with pytest.raises(RuntimeError, match="browser reached"):
            await steps.apply(session, run, ctx, {"vacancy_id": vacancy.id})
        page.assert_awaited_once()
    else:
        await steps.apply(session, run, ctx, {"vacancy_id": vacancy.id})
        page.assert_not_awaited()
        assert decision.status == VacancyStatus.FILTERED_OUT.value
        assert decision.skip_reason == SkipReason.REGION.value
