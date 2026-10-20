"""Управление прогоном (§22, §26)."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import Session
from app.core.enums import BotMode, RuntimeMode, StopReason
from app.pipeline.runner import bot
from app.storage.models import Resume
from app.storage.repositories import crud

router = APIRouter(prefix="/bot", tags=["Бот"])


class StartRequest(BaseModel):
    resume_id: int
    mode: BotMode = BotMode.MANUAL
    runtime_mode: RuntimeMode = RuntimeMode.DRY_RUN
    search_profile_id: int | None = None
    # Заново проанализировать вакансии, отклонённые моделью, по текущим правилам
    reanalyze_rejected: bool = False


@router.get("/status", summary="Состояние бота")
async def status() -> dict[str, Any]:
    return await bot.status_dict()


@router.post("/start", summary="Запустить прогон")
async def start(payload: StartRequest, session: Session) -> dict[str, Any]:
    await crud.get_or_404(session, Resume, payload.resume_id, "Резюме")
    run_id = await bot.start(
        resume_id=payload.resume_id,
        mode=payload.mode.value,
        runtime_mode=payload.runtime_mode.value,
        search_profile_id=payload.search_profile_id,
        reanalyze_rejected=payload.reanalyze_rejected,
    )
    return {"run_id": run_id} | await bot.status_dict()


@router.post("/pause", summary="Пауза")
async def pause() -> dict[str, Any]:
    await bot.pause()
    return await bot.status_dict()


@router.post("/resume", summary="Продолжить")
async def resume() -> dict[str, Any]:
    await bot.resume()
    return await bot.status_dict()


@router.post("/stop", summary="Остановить")
async def stop() -> dict[str, Any]:
    await bot.stop(StopReason.USER)
    return await bot.status_dict()
