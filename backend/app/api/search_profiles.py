"""Поисковые профили и запросы (§8, §26)."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import Session
from app.core.enums import RemoteMode
from app.storage.models import Resume, SearchProfile, SearchQuery
from app.storage.repositories import crud

router = APIRouter(prefix="/search-profiles", tags=["Поисковые профили"])


class QueryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


class ProfileIn(BaseModel):
    resume_id: int
    name: str = Field(min_length=1, max_length=200)
    enabled: bool = True
    priority: int = 1
    queries: list[str] = Field(default_factory=list)
    remote_mode: RemoteMode = RemoteMode.ANY
    min_salary: int | None = None
    currency: str = "KZT"
    allow_unknown_salary: bool = True
    experience_levels: list[str] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)
    max_age_days: int | None = 7
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    max_vacancies_per_run: int = Field(default=25, ge=1, le=500)


class ProfilePatch(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    priority: int | None = None
    queries: list[str] | None = None
    remote_mode: RemoteMode | None = None
    min_salary: int | None = None
    currency: str | None = None
    allow_unknown_salary: bool | None = None
    experience_levels: list[str] | None = None
    areas: list[str] | None = None
    max_age_days: int | None = None
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    max_vacancies_per_run: int | None = Field(default=None, ge=1, le=500)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int
    name: str
    enabled: bool
    priority: int
    remote_mode: str
    min_salary: int | None
    currency: str
    allow_unknown_salary: bool
    experience_levels: list[Any]
    areas: list[Any]
    max_age_days: int | None
    include_keywords: list[Any]
    exclude_keywords: list[Any]
    max_vacancies_per_run: int
    queries: list[QueryOut]


async def _replace_queries(session: Session, profile: SearchProfile, texts: list[str]) -> None:
    await crud.remove_where(session, SearchQuery, search_profile_id=profile.id)
    for text in texts:
        if text.strip():
            session.add(SearchQuery(search_profile_id=profile.id, text=text.strip()))
    await session.commit()


@router.get("", response_model=list[ProfileOut], summary="Профили резюме")
async def list_profiles(session: Session, resume_id: int) -> list[SearchProfile]:
    return await crud.list_all(
        session, SearchProfile, order_by=SearchProfile.priority, resume_id=resume_id
    )


@router.post("", response_model=ProfileOut, status_code=201, summary="Создать профиль")
async def create_profile(payload: ProfileIn, session: Session) -> SearchProfile:
    await crud.get_or_404(session, Resume, payload.resume_id, "Резюме")
    data = payload.model_dump()
    queries = data.pop("queries")
    profile = await crud.create(session, SearchProfile, data)
    await _replace_queries(session, profile, queries)
    await session.refresh(profile)
    return profile


@router.patch("/{profile_id}", response_model=ProfileOut, summary="Изменить профиль")
async def patch_profile(profile_id: int, payload: ProfilePatch, session: Session) -> SearchProfile:
    profile = await crud.get_or_404(session, SearchProfile, profile_id, "Поисковый профиль")
    data = payload.model_dump(exclude_unset=True)
    queries = data.pop("queries", None)
    profile = await crud.update(session, profile, data)
    if queries is not None:
        await _replace_queries(session, profile, queries)
        await session.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=204, summary="Удалить профиль")
async def delete_profile(profile_id: int, session: Session) -> None:
    profile = await crud.get_or_404(session, SearchProfile, profile_id, "Поисковый профиль")
    await crud.remove(session, profile)
