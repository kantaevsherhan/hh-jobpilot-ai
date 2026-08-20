"""Главный цикл прогона (§22).

Один воркер, последовательно: параллелизм упрётся в 4 ГБ VRAM (§2).
Всё состояние — в БД, в памяти живёт только текущая задача.
"""

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    BotMode,
    EventLevel,
    JobState,
    JobType,
    RunStatus,
    RuntimeMode,
    StopReason,
)
from app.core.errors import AppError, ConflictError
from app.core.logging import get_logger
from app.pipeline import events, queue
from app.pipeline.context import load_context
from app.pipeline.steps import HANDLERS
from app.storage import session as db
from app.storage.models import Resume, Run
from app.storage.models.base import utcnow

log = get_logger(__name__)


async def find_resumable(session: AsyncSession) -> Run | None:
    """Последний прогон, который можно продолжить.

    Очередь живёт в БД, а run_id — только в памяти процесса. После
    перезапуска приложения продолжать всё равно должно быть можно (§22).
    """
    resumable = (RunStatus.STOPPED.value, RunStatus.PAUSED.value, RunStatus.INTERRUPTED.value)
    runs = list(
        (
            await session.scalars(
                select(Run).where(Run.status.in_(resumable)).order_by(Run.id.desc()).limit(10)
            )
        ).all()
    )
    for run in runs:
        if await queue.pending_count(session, run.id):
            return run
    return None


class BotRunner:
    """Состояние бота на процесс. Прогон один: параллельные прогоны разных
    резюме в v1 не поддерживаются (§7)."""

    def __init__(self) -> None:
        self.run_id: int | None = None
        self.status: RunStatus = RunStatus.IDLE
        self._task: asyncio.Task[None] | None = None
        self._pause = asyncio.Event()
        self._stop = asyncio.Event()
        self.current_job: str | None = None
        self.consecutive_errors = 0

    @property
    def is_busy(self) -> bool:
        return self._task is not None and not self._task.done()

    async def status_dict(self) -> dict[str, Any]:
        counters: dict[str, Any] = {}
        pending = 0
        if self.run_id is not None:
            async with db.session_factory()() as session:
                run = await session.get(Run, self.run_id)
                if run is not None:
                    counters = dict(run.counters_json or {})
                    self.status = RunStatus(run.status)
                pending = await queue.pending_count(session, self.run_id)
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "is_busy": self.is_busy,
            "current_job": self.current_job,
            "pending_jobs": pending,
            "counters": counters,
            "consecutive_errors": self.consecutive_errors,
        }

    async def start(
        self,
        *,
        resume_id: int,
        mode: str = BotMode.MANUAL,
        runtime_mode: str = RuntimeMode.DRY_RUN,
        search_profile_id: int | None = None,
    ) -> int:
        if self.is_busy:
            raise ConflictError("BOT_ALREADY_RUNNING", "Прогон уже идёт")

        async with db.session_factory()() as session:
            ctx = await load_context(session, resume_id, search_profile_id)
            if not ctx.profiles:
                raise ConflictError(
                    "NO_SEARCH_PROFILES",
                    "У резюме нет включённых поисковых профилей",
                    recoverable=False,
                )

            # Первый прогон нового резюме принудительно идёт в DRY_RUN (§20)
            effective_runtime = runtime_mode
            if not ctx.resume.has_completed_run and runtime_mode == RuntimeMode.LIVE:
                effective_runtime = RuntimeMode.DRY_RUN
                log.info("Первый прогон резюме %s переведён в DRY_RUN", resume_id)

            run = Run(
                resume_id=resume_id,
                search_profile_id=search_profile_id,
                mode=str(mode),
                runtime_mode=str(effective_runtime),
                status=RunStatus.RUNNING.value,
                counters_json={},
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)

            await queue.add_many(
                session,
                run.id,
                JobType.SEARCH,
                [{"search_profile_id": profile.id} for profile in ctx.profiles],
            )
            await events.log_event(
                session,
                run.id,
                "run_started",
                f"Прогон запущен: режим {mode}, {effective_runtime}",
                payload={"forced_dry_run": effective_runtime != runtime_mode},
            )

        self.run_id = run.id
        self.status = RunStatus.RUNNING
        self.consecutive_errors = 0
        self._pause.clear()
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(run.id, resume_id, search_profile_id))
        return run.id

    async def pause(self) -> None:
        """Текущая задача доводится до конца, следующая не берётся."""
        self._pause.set()
        await self._set_status(RunStatus.PAUSED)

    async def resume(self) -> None:
        """Продолжить прогон.

        Пауза — просто снять флаг. Но прогон мог быть и остановлен: например,
        отвалился провайдер (§14). Тогда воркера уже нет, и «Продолжить»
        обязано поднять его заново — задачи ждут в очереди с той же вакансии.
        """
        self._pause.clear()

        if self.is_busy:
            await self._set_status(RunStatus.RUNNING)
            return

        async with db.session_factory()() as session:
            run = (
                await session.get(Run, self.run_id)
                if self.run_id is not None
                else await find_resumable(session)
            )
            if run is None:
                raise ConflictError(
                    "NO_RUN", "Нечего продолжать: незавершённых прогонов нет", recoverable=False
                )
            self.run_id = run.id
            pending = await queue.pending_count(session, run.id)
            if pending == 0:
                raise ConflictError(
                    "NOTHING_TO_RESUME",
                    "В прогоне не осталось задач. Запустите новый.",
                    recoverable=False,
                )
            run.status = RunStatus.RUNNING.value
            run.ended_at = None
            run.stop_reason = None
            await session.commit()
            run_id, resume_id, profile_id = run.id, run.resume_id, run.search_profile_id

        self.status = RunStatus.RUNNING
        self.consecutive_errors = 0
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(run_id, resume_id, profile_id))

    async def stop(self, reason: StopReason = StopReason.USER) -> None:
        self._stop.set()
        self._pause.clear()
        if self._task is not None:
            await asyncio.wait([self._task], timeout=90)
        await self._finish(reason)

    async def _loop(self, run_id: int, resume_id: int, search_profile_id: int | None) -> None:
        from app.browser.manager import browser

        try:
            async with db.session_factory()() as session:
                ctx = await load_context(session, resume_id, search_profile_id)
                max_errors = int(ctx.limits.get("max_consecutive_errors", 5))

            processed = 0
            while not self._stop.is_set():
                if self._pause.is_set():
                    await asyncio.sleep(1)
                    continue

                async with db.session_factory()() as session:
                    job = await queue.take_next(session, run_id)
                    if job is None:
                        await self._finish(StopReason.FINISHED)
                        return

                    run = await session.get_one(Run, run_id)
                    ctx = await load_context(session, resume_id, search_profile_id)
                    self.current_job = job.type
                    handler = HANDLERS.get(job.type)

                    if handler is None:
                        await queue.finish(session, job, JobState.SKIPPED, "Неизвестный тип задачи")
                        continue

                    try:
                        await handler(session, run, ctx, job.payload_json)
                        await queue.finish(session, job, JobState.DONE)
                        await session.commit()
                        self.consecutive_errors = 0
                    except AppError as exc:
                        await self._on_error(session, run, job, exc, max_errors)
                        if self._stop.is_set():
                            return
                        await ctx.delays.pause("on_error")
                    except Exception as exc:
                        await self._on_error(
                            session,
                            run,
                            job,
                            AppError("UNEXPECTED", str(exc), technical_details=repr(exc)),
                            max_errors,
                        )
                        if self._stop.is_set():
                            return

                processed += 1
                if ctx.delays.needs_long_break(processed):
                    seconds = await ctx.delays.long_break()
                    async with db.session_factory()() as session:
                        await events.log_event(
                            session,
                            run_id,
                            "long_pause",
                            f"Длинная пауза {round(seconds)} сек",
                            level=EventLevel.DEBUG,
                        )
        finally:
            self.current_job = None
            if self.status == RunStatus.RUNNING:
                await self._finish(StopReason.FINISHED)
            await browser.stop()

    async def _on_error(
        self,
        session: Any,
        run: Run,
        job: Any,
        exc: AppError,
        max_errors: int,
    ) -> None:
        self.consecutive_errors += 1
        await queue.finish(session, job, JobState.FAILED, exc.human_message)

        run.last_error_code = exc.error_code
        run.last_error_step = job.type
        counters = dict(run.counters_json or {})
        counters["errors"] = int(counters.get("errors", 0)) + 1
        run.counters_json = counters
        await session.commit()

        await events.log_event(
            session,
            run.id,
            "error",
            f"{job.type}: {exc.human_message}",
            level=EventLevel.ERROR,
            payload=exc.to_dict(),
        )
        log.warning("Ошибка в задаче %s: %s", job.type, exc.human_message)

        # Провайдер недоступен — останавливаемся, а не переходим на слабую модель (§14)
        if exc.error_code in {"PROVIDER_UNAVAILABLE", "PROVIDER_TIMEOUT"}:
            job.state = JobState.PENDING.value
            await session.commit()
            self._stop.set()
            await self._finish(StopReason.PROVIDER_UNAVAILABLE)
            return

        if exc.error_code == "LIMIT_REACHED":
            self._stop.set()
            await self._finish(StopReason.LIMIT_REACHED)
            return

        if exc.error_code in {"HH_CAPTCHA", "HH_SESSION_EXPIRED"}:
            self._stop.set()
            await self._finish(StopReason.NEEDS_USER_ACTION)
            return

        if self.consecutive_errors >= max_errors:
            self._stop.set()
            await self._finish(StopReason.TOO_MANY_ERRORS)

    async def _set_status(self, status: RunStatus) -> None:
        self.status = status
        if self.run_id is None:
            return
        async with db.session_factory()() as session:
            run = await session.get(Run, self.run_id)
            if run is not None:
                run.status = status.value
                await session.commit()

    async def _finish(self, reason: StopReason) -> None:
        if self.run_id is None:
            return
        async with db.session_factory()() as session:
            run = await session.get(Run, self.run_id)
            if run is None or run.status in {RunStatus.FINISHED.value, RunStatus.STOPPED.value}:
                return
            run.status = (
                RunStatus.FINISHED.value
                if reason == StopReason.FINISHED
                else RunStatus.STOPPED.value
            )
            run.stop_reason = reason.value
            run.ended_at = utcnow()

            await session.commit()

            resume = await session.get(Resume, run.resume_id)
            if resume is not None and not resume.has_completed_run:
                resume.has_completed_run = True
                await session.commit()

            await events.log_event(
                session, run.id, "run_finished", f"Прогон завершён: {reason.value}"
            )
        self.status = RunStatus(
            RunStatus.FINISHED if reason == StopReason.FINISHED else RunStatus.STOPPED
        )


bot = BotRunner()
