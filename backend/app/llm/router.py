"""Маршрутизация шагов пайплайна по провайдерам (§14).

Провайдер выбирается не глобально, а на каждый шаг: анализ гоняется 25 раз
за прогон и ему хватает локальной модели, письмо пишется один раз и там
разница в качестве видна сразу.

Сессия БД сюда попадает намеренно: роутеру нужны настройки провайдеров и
маршрутов, то есть конфигурация. Бизнес-данные (вакансии, письма, отклики)
слой llm/ не читает и не пишет — этим занимается pipeline/.
"""

import asyncio
import time
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.logging import get_logger
from app.llm.base import LLMProvider, LLMResult, extract_json
from app.llm.providers import REGISTRY
from app.storage.models import LLMProvider as ProviderRow
from app.storage.repositories import settings as settings_repo

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

RETRY_HINT = "\n\nВерни строго JSON по схеме, без пояснений и без текста вокруг."


def build_provider(row: ProviderRow) -> LLMProvider:
    cls = REGISTRY.get(row.type)
    if cls is None:
        raise AppError("PROVIDER_UNAVAILABLE", f"Неизвестный тип провайдера: {row.type}")
    return cls(
        name=row.name,
        model=row.model,
        base_url=row.base_url,
        api_key=row.api_key,
        temperature=row.temperature,
        timeout_sec=row.timeout_sec,
        extra=row.extra_json,
    )


async def provider_for_step(session: AsyncSession, step: str) -> LLMProvider:
    """Провайдер для шага. Если маршрут не задан — берём единственный
    включённый; если их несколько, требуем настроить маршрутизацию явно."""
    routing = await settings_repo.get_one(session, "llm_routing")
    provider_id = routing.get(step)

    if provider_id is not None:
        row = await session.get(ProviderRow, int(provider_id))
        if row is None or not row.is_enabled:
            raise AppError(
                "PROVIDER_UNAVAILABLE",
                f"Провайдер для шага «{step}» выключен или удалён. Проверьте настройки моделей.",
                step=step,
            )
        return build_provider(row)

    enabled = list((await session.scalars(select(ProviderRow).where(ProviderRow.is_enabled))).all())
    if not enabled:
        raise AppError(
            "PROVIDER_UNAVAILABLE",
            "Ни одного провайдера не настроено. Откройте «Модели и провайдеры».",
            step=step,
        )
    return build_provider(enabled[0])


async def call(provider: LLMProvider, prompt: str, schema: type[T]) -> tuple[T, LLMResult]:
    """Вызвать модель и провалидировать ответ.

    Одна повторная попытка при мусоре (§15) и одна — при недоступности
    провайдера через 5 секунд (§14). Молчаливого фолбэка на другую модель нет.
    """
    started = time.monotonic()
    raw = await _complete_with_retry(provider, prompt)
    retried = False

    try:
        parsed = schema.model_validate(extract_json(raw))
    except (AppError, ValidationError) as first_error:
        log.warning("Невалидный ответ %s, повторяю: %s", provider.name, first_error)
        retried = True
        raw = await _complete_with_retry(provider, prompt + RETRY_HINT)
        try:
            parsed = schema.model_validate(extract_json(raw))
        except (AppError, ValidationError) as exc:
            raise AppError(
                "INVALID_LLM_RESPONSE",
                "Модель дважды вернула ответ, не подходящий под схему",
                technical_details=f"{exc}\n\nОТВЕТ:\n{raw[:2000]}",
            ) from exc

    return parsed, LLMResult(
        data=parsed.model_dump(),
        raw=raw,
        provider=provider.name,
        model=provider.model,
        elapsed_sec=round(time.monotonic() - started, 2),
        retried=retried,
    )


async def _complete_with_retry(provider: LLMProvider, prompt: str) -> str:
    try:
        return await provider.complete(prompt)
    except AppError as exc:
        if exc.error_code not in {"PROVIDER_UNAVAILABLE", "PROVIDER_TIMEOUT"}:
            raise
        log.warning("Провайдер %s недоступен, повтор через 5 сек", provider.name)
        await asyncio.sleep(5)
        return await provider.complete(prompt)


async def test_provider(row: ProviderRow) -> dict[str, Any]:
    """Тестовый вызов из UI: показать ответ и время."""
    provider = build_provider(row)
    started = time.monotonic()
    try:
        raw = await provider.complete(
            'Ответь строго JSON: {"ok": true, "model": "<название модели>"}'
        )
    except AppError as exc:
        return {"ok": False, "error": exc.human_message, "details": exc.technical_details}
    finally:
        await provider.close()
    return {
        "ok": True,
        "response": raw[:500],
        "elapsed_sec": round(time.monotonic() - started, 2),
    }
