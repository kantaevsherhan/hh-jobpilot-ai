"""Резюме: CRUD, дублирование, архивация (§7)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import Session
from app.core.errors import ConflictError
from app.llm.steps.resume_digest import build_digest, digest_to_skills
from app.storage.models import Application, Resume, ResumeSkill
from app.storage.models.base import utcnow
from app.storage.repositories import crud

router = APIRouter(prefix="/resumes", tags=["Резюме"])


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_core: bool


class ResumeIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    raw_text: str = ""
    allowed_facts: str = ""
    hh_resume_url: str | None = None
    hh_resume_id: str | None = None
    letter_languages: list[str] = Field(default_factory=lambda: ["ru"])
    min_score: int = Field(default=75, ge=0, le=100)
    auto_apply_score: int = Field(default=90, ge=0, le=100)


class ResumePatch(BaseModel):
    """Частичное обновление: пришедшие поля меняются, остальные остаются как есть."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    raw_text: str | None = None
    allowed_facts: str | None = None
    hh_resume_url: str | None = None
    hh_resume_id: str | None = None
    letter_languages: list[str] | None = None
    min_score: int | None = Field(default=None, ge=0, le=100)
    auto_apply_score: int | None = Field(default=None, ge=0, le=100)
    digest_json: dict[str, Any] | None = None
    is_active: bool | None = None
    is_archived: bool | None = None


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    raw_text: str
    allowed_facts: str
    hh_resume_url: str | None
    hh_resume_id: str | None
    letter_languages: list[str]
    min_score: int
    auto_apply_score: int
    digest_json: dict[str, Any] | None
    digest_updated_at: datetime | None
    is_active: bool
    is_archived: bool
    has_completed_run: bool
    skills: list[SkillOut]
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[ResumeOut], summary="Список резюме")
async def list_resumes(session: Session, include_archived: bool = False) -> list[Resume]:
    return await crud.list_all(
        session,
        Resume,
        order_by=Resume.id,
        is_archived=None if include_archived else False,
    )


@router.post("", response_model=ResumeOut, status_code=201, summary="Создать резюме")
async def create_resume(payload: ResumeIn, session: Session) -> Resume:
    return await crud.create(session, Resume, payload.model_dump())


@router.get("/{resume_id}", response_model=ResumeOut, summary="Резюме по id")
async def get_resume(resume_id: int, session: Session) -> Resume:
    return await crud.get_or_404(session, Resume, resume_id, "Резюме")


@router.patch("/{resume_id}", response_model=ResumeOut, summary="Изменить резюме")
async def patch_resume(resume_id: int, payload: ResumePatch, session: Session) -> Resume:
    resume = await crud.get_or_404(session, Resume, resume_id, "Резюме")
    return await crud.update(session, resume, payload.model_dump(exclude_unset=True))


@router.post("/{resume_id}/duplicate", response_model=ResumeOut, summary="Дублировать резюме")
async def duplicate_resume(resume_id: int, session: Session) -> Resume:
    src = await crud.get_or_404(session, Resume, resume_id, "Резюме")
    copy = await crud.create(
        session,
        Resume,
        {
            "name": f"{src.name} (копия)",
            "raw_text": src.raw_text,
            "allowed_facts": src.allowed_facts,
            "hh_resume_url": src.hh_resume_url,
            "hh_resume_id": src.hh_resume_id,
            "letter_languages": list(src.letter_languages),
            "min_score": src.min_score,
            "auto_apply_score": src.auto_apply_score,
            "digest_json": src.digest_json,
            "digest_updated_at": src.digest_updated_at,
        },
    )
    for skill in src.skills:
        session.add(ResumeSkill(resume_id=copy.id, name=skill.name, is_core=skill.is_core))
    await session.commit()
    await session.refresh(copy)
    return copy


@router.post("/{resume_id}/archive", response_model=ResumeOut, summary="Архивировать резюме")
async def archive_resume(resume_id: int, session: Session) -> Resume:
    resume = await crud.get_or_404(session, Resume, resume_id, "Резюме")
    return await crud.update(session, resume, {"is_archived": True, "is_active": False})


@router.delete("/{resume_id}", status_code=204, summary="Удалить резюме")
async def delete_resume(resume_id: int, session: Session) -> None:
    resume = await crud.get_or_404(session, Resume, resume_id, "Резюме")
    # История откликов не должна исчезать вместе с резюме (§7)
    sent = await crud.count(session, Application, resume_id=resume.id)
    if sent:
        raise ConflictError(
            "RESUME_HAS_APPLICATIONS",
            f"По резюме отправлено откликов: {sent}. Такое резюме можно только архивировать.",
            recoverable=False,
        )
    await crud.remove(session, resume)


class SkillsIn(BaseModel):
    skills: list[SkillOut | dict[str, Any]] = Field(default_factory=list)


@router.put("/{resume_id}/skills", response_model=list[SkillOut], summary="Заменить список навыков")
async def replace_skills(resume_id: int, payload: SkillsIn, session: Session) -> list[ResumeSkill]:
    resume = await crud.get_or_404(session, Resume, resume_id, "Резюме")
    await crud.remove_where(session, ResumeSkill, resume_id=resume.id)
    for item in payload.skills:
        data = item if isinstance(item, dict) else item.model_dump()
        session.add(
            ResumeSkill(
                resume_id=resume.id,
                name=str(data["name"]),
                is_core=bool(data.get("is_core", False)),
            )
        )
    await session.commit()
    return await crud.list_all(session, ResumeSkill, order_by=ResumeSkill.id, resume_id=resume.id)


@router.post("/{resume_id}/digest", response_model=ResumeOut, summary="Пересобрать выжимку")
async def rebuild_digest(resume_id: int, session: Session) -> Resume:
    resume = await crud.get_or_404(session, Resume, resume_id, "Резюме")
    if not resume.raw_text.strip():
        raise ConflictError(
            "RESUME_TEXT_EMPTY",
            "Сначала вставьте текст резюме — выжимку не из чего собирать.",
            recoverable=False,
        )

    digest, _ = await build_digest(session, resume.raw_text)
    await crud.update(
        session,
        resume,
        {"digest_json": digest.model_dump(), "digest_updated_at": utcnow()},
    )

    # Навыки пересобираются из выжимки: правки руками при пересборке теряются,
    # это ожидаемо — выжимка объявлена источником списка навыков (§7)
    await crud.remove_where(session, ResumeSkill, resume_id=resume.id)
    for name, is_core in digest_to_skills(digest):
        session.add(ResumeSkill(resume_id=resume.id, name=name, is_core=is_core))
    await session.commit()
    await session.refresh(resume)
    return resume
