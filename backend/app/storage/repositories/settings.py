"""Настройки приложения: чтение с подстановкой дефолтов и запись."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.defaults import DEFAULT_SETTINGS
from app.storage.models import Setting


async def get_all(session: AsyncSession) -> dict[str, Any]:
    """Все настройки. Ключи, которых нет в базе, отдаются из дефолтов —
    иначе после добавления новой настройки старая база ломает приложение."""
    stored = {s.key: s.value_json for s in (await session.scalars(select(Setting))).all()}
    return {key: stored.get(key, default) for key, default in DEFAULT_SETTINGS.items()} | {
        key: value for key, value in stored.items() if key not in DEFAULT_SETTINGS
    }


async def get_one(session: AsyncSession, key: str) -> Any:
    setting = await session.get(Setting, key)
    if setting is not None:
        return setting.value_json
    return DEFAULT_SETTINGS.get(key, {})


async def put(session: AsyncSession, key: str, value: Any) -> Any:
    setting = await session.get(Setting, key)
    if setting is None:
        setting = Setting(key=key, value_json=value)
        session.add(setting)
    else:
        setting.value_json = value
    await session.commit()
    return value


async def patch_many(session: AsyncSession, values: dict[str, Any]) -> dict[str, Any]:
    for key, value in values.items():
        await put(session, key, value)
    return await get_all(session)
