"""Скиллы: правила стиля, которые дописываются к выбранным промптам."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.deps import Session
from app.core.enums import PROMPT_KEY_LABELS, PromptKey
from app.llm.prompts import SKILL_TARGETS
from app.storage.models import Skill
from app.storage.repositories import crud

router = APIRouter(prefix="/skills", tags=["Скиллы"])


def _known_keys(keys: list[str] | None) -> list[str] | None:
    if keys is None:
        return None
    unknown = [key for key in keys if key not in SKILL_TARGETS]
    if unknown:
        raise ValueError(f"К этим промптам скилл подключить нельзя: {', '.join(unknown)}")
    return list(dict.fromkeys(keys))


class SkillIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    prompt_keys: list[str] = Field(default_factory=list)
    is_enabled: bool = True

    _check_keys = field_validator("prompt_keys")(_known_keys)


class SkillPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    prompt_keys: list[str] | None = None
    is_enabled: bool | None = None

    _check_keys = field_validator("prompt_keys")(_known_keys)


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    content: str
    prompt_keys: list[str]
    is_enabled: bool


class SkillTarget(BaseModel):
    key: str
    title: str


@router.get("", response_model=list[SkillOut], summary="Список скиллов")
async def list_skills(session: Session) -> list[Skill]:
    return await crud.list_all(session, Skill, order_by=Skill.id)


@router.get("/targets", response_model=list[SkillTarget], summary="К каким промптам подключать")
async def targets() -> list[SkillTarget]:
    return [SkillTarget(key=key, title=PROMPT_KEY_LABELS[PromptKey(key)]) for key in SKILL_TARGETS]


@router.post("", response_model=SkillOut, status_code=201, summary="Добавить скилл")
async def create_skill(payload: SkillIn, session: Session) -> Skill:
    return await crud.create(session, Skill, payload.model_dump())


@router.patch("/{skill_id}", response_model=SkillOut, summary="Изменить скилл")
async def patch_skill(skill_id: int, payload: SkillPatch, session: Session) -> Skill:
    row = await crud.get_or_404(session, Skill, skill_id, "Скилл")
    return await crud.update(session, row, payload.model_dump(exclude_unset=True))


@router.delete("/{skill_id}", status_code=204, summary="Удалить скилл")
async def delete_skill(skill_id: int, session: Session) -> None:
    row = await crud.get_or_404(session, Skill, skill_id, "Скилл")
    await crud.remove(session, row)
