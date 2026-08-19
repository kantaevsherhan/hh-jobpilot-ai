"""Настройки приложения (§29)."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import Session
from app.storage.repositories import settings as settings_repo

router = APIRouter(tags=["Настройки"])


@router.get("/settings", summary="Все настройки")
async def get_settings(session: Session) -> dict[str, Any]:
    return await settings_repo.get_all(session)


@router.patch("/settings", summary="Изменить настройки")
async def patch_settings(payload: dict[str, Any], session: Session) -> dict[str, Any]:
    return await settings_repo.patch_many(session, payload)
