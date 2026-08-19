"""Промпты: чтение, правка, сброс к дефолту (§14)."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.api.deps import Session
from app.core.enums import PROMPT_KEY_LABELS, PromptKey
from app.llm import prompts as prompts_lib
from app.storage.models import Prompt
from app.storage.repositories import crud

router = APIRouter(prefix="/prompts", tags=["Промпты"])


class PromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    title: str
    content: str
    updated_at: datetime
    is_default: bool = False


class PromptPatch(BaseModel):
    content: str


async def _by_key(session: Session, key: str) -> Prompt:
    rows = await crud.list_all(session, Prompt, key=key)
    if rows:
        return rows[0]
    return await crud.create(
        session,
        Prompt,
        {
            "key": key,
            "title": PROMPT_KEY_LABELS.get(key, key),
            "content": prompts_lib.default_text(key),
        },
    )


def _with_default_flag(row: Prompt) -> PromptOut:
    out = PromptOut.model_validate(row)
    return out.model_copy(update={"is_default": row.content == prompts_lib.default_text(row.key)})


@router.get("", response_model=list[PromptOut], summary="Все промпты")
async def list_prompts(session: Session) -> list[PromptOut]:
    await prompts_lib.seed_defaults(session)
    rows = await crud.list_all(session, Prompt, order_by=Prompt.id)
    return [_with_default_flag(row) for row in rows]


@router.patch("/{key}", response_model=PromptOut, summary="Изменить промпт")
async def patch_prompt(key: PromptKey, payload: PromptPatch, session: Session) -> PromptOut:
    row = await _by_key(session, key.value)
    return _with_default_flag(await crud.update(session, row, {"content": payload.content}))


@router.post("/{key}/reset", response_model=PromptOut, summary="Вернуть промпт к дефолту")
async def reset_prompt(key: PromptKey, session: Session) -> PromptOut:
    row = await _by_key(session, key.value)
    content = prompts_lib.default_text(key.value)
    return _with_default_flag(await crud.update(session, row, {"content": content}))
