"""Провайдеры моделей и маршрутизация шагов (§14)."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import Session
from app.core.enums import PromptKey, ProviderType
from app.llm import router as llm_router
from app.storage.models import LLMProvider
from app.storage.repositories import crud
from app.storage.repositories import settings as settings_repo

router = APIRouter(prefix="/providers", tags=["Провайдеры"])


def mask(key: str | None) -> str | None:
    """Ключ наружу целиком не отдаётся никогда (§29)."""
    if not key:
        return None
    return f"{key[:3]}…{key[-4:]}" if len(key) > 10 else "…"


class ProviderIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: ProviderType = ProviderType.OLLAMA
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float = Field(default=0.3, ge=0, le=2)
    timeout_sec: int = Field(default=300, ge=5, le=3600)
    extra_json: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class ProviderPatch(BaseModel):
    name: str | None = None
    type: ProviderType | None = None
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    timeout_sec: int | None = Field(default=None, ge=5, le=3600)
    extra_json: dict[str, Any] | None = None
    is_enabled: bool | None = None


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    base_url: str | None
    model: str | None
    temperature: float
    timeout_sec: int
    extra_json: dict[str, Any]
    is_enabled: bool
    api_key_masked: str | None = None

    @classmethod
    def of(cls, row: LLMProvider) -> "ProviderOut":
        return cls.model_validate(row).model_copy(update={"api_key_masked": mask(row.api_key)})


@router.get("", response_model=list[ProviderOut], summary="Список провайдеров")
async def list_providers(session: Session) -> list[ProviderOut]:
    rows = await crud.list_all(session, LLMProvider, order_by=LLMProvider.id)
    return [ProviderOut.of(row) for row in rows]


@router.post("", response_model=ProviderOut, status_code=201, summary="Добавить провайдера")
async def create_provider(payload: ProviderIn, session: Session) -> ProviderOut:
    row = await crud.create(session, LLMProvider, payload.model_dump())
    return ProviderOut.of(row)


@router.patch("/{provider_id}", response_model=ProviderOut, summary="Изменить провайдера")
async def patch_provider(provider_id: int, payload: ProviderPatch, session: Session) -> ProviderOut:
    row = await crud.get_or_404(session, LLMProvider, provider_id, "Провайдер")
    data = payload.model_dump(exclude_unset=True)
    # Пустая строка в ключе означает «не менять»: UI показывает маску, а не сам ключ
    if data.get("api_key") == "":
        data.pop("api_key")
    return ProviderOut.of(await crud.update(session, row, data))


@router.delete("/{provider_id}", status_code=204, summary="Удалить провайдера")
async def delete_provider(provider_id: int, session: Session) -> None:
    row = await crud.get_or_404(session, LLMProvider, provider_id, "Провайдер")
    routing: dict[str, Any] = await settings_repo.get_one(session, "llm_routing")
    cleaned = {step: pid for step, pid in routing.items() if int(pid) != provider_id}
    if cleaned != routing:
        await settings_repo.put(session, "llm_routing", cleaned)
    await crud.remove(session, row)


@router.post("/{provider_id}/test", summary="Тестовый вызов провайдера")
async def test_provider(provider_id: int, session: Session) -> dict[str, Any]:
    row = await crud.get_or_404(session, LLMProvider, provider_id, "Провайдер")
    return await llm_router.test_provider(row)


class Routing(BaseModel):
    """step → llm_providers.id. Шаги — ключи промптов (§14)."""

    routing: dict[str, int] = Field(default_factory=dict)


@router.get("/routing/current", response_model=Routing, summary="Маршрутизация шагов")
async def get_routing(session: Session) -> Routing:
    stored: dict[str, Any] = await settings_repo.get_one(session, "llm_routing")
    return Routing(routing={key: int(value) for key, value in stored.items()})


@router.put("/routing/current", response_model=Routing, summary="Сохранить маршрутизацию")
async def put_routing(payload: Routing, session: Session) -> Routing:
    known = {key.value for key in PromptKey}
    cleaned = {step: pid for step, pid in payload.routing.items() if step in known}
    await settings_repo.put(session, "llm_routing", cleaned)
    return Routing(routing=cleaned)
