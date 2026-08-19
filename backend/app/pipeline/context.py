"""Данные, которые нужны шагам прогона и не меняются в его ходе."""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.company import CompanyRuleSpec
from app.filters.engine import ProfileRules
from app.pipeline.delays import Delays
from app.storage.models import CompanyRule, Resume, SearchProfile
from app.storage.repositories import settings as settings_repo


@dataclass(slots=True)
class RunContext:
    resume: Resume
    profiles: list[SearchProfile]
    company_rules: list[CompanyRuleSpec]
    delays: Delays
    settings: dict[str, Any] = field(default_factory=dict)

    @property
    def limits(self) -> dict[str, Any]:
        value: dict[str, Any] = self.settings.get("limits", {})
        return value

    @property
    def llm_settings(self) -> dict[str, Any]:
        value: dict[str, Any] = self.settings.get("llm", {})
        return value

    def rules_for(self, profile: SearchProfile) -> ProfileRules:
        return ProfileRules(
            min_salary=profile.min_salary,
            currency=profile.currency,
            allow_unknown_salary=profile.allow_unknown_salary,
            remote_mode=profile.remote_mode,
            experience_levels=list(profile.experience_levels),
            max_age_days=profile.max_age_days,
            include_keywords=list(profile.include_keywords),
            exclude_keywords=list(profile.exclude_keywords),
            currency_rates=self.settings.get("currency_rates", {}),
            tax_rate=float(self.settings.get("tax_rate", 0.10)),
        )


async def load_context(
    session: AsyncSession,
    resume_id: int,
    search_profile_id: int | None = None,
) -> RunContext:
    resume = await session.get_one(Resume, resume_id)

    query = select(SearchProfile).where(SearchProfile.resume_id == resume_id, SearchProfile.enabled)
    if search_profile_id is not None:
        query = select(SearchProfile).where(SearchProfile.id == search_profile_id)
    profiles = list((await session.scalars(query.order_by(SearchProfile.priority))).all())

    # Общие правила (resume_id IS NULL) действуют для всех резюме (§12)
    rule_rows = list(
        (
            await session.scalars(
                select(CompanyRule).where(
                    CompanyRule.enabled,
                    (CompanyRule.resume_id.is_(None)) | (CompanyRule.resume_id == resume_id),
                )
            )
        ).all()
    )

    app_settings = await settings_repo.get_all(session)

    return RunContext(
        resume=resume,
        profiles=profiles,
        company_rules=[
            CompanyRuleSpec(
                match_type=row.match_type,
                value=row.value,
                action=row.action,
                case_sensitive=row.case_sensitive,
                score_delta=row.score_delta,
                note=row.note,
            )
            for row in rule_rows
        ],
        delays=Delays(app_settings.get("delays")),
        settings=app_settings,
    )
