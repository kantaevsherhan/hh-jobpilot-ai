"""Точка входа бэкенда."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import get_logger, setup_logging
from app.llm.prompts import seed_default_provider, seed_defaults
from app.storage.session import SessionMaker

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    for directory in (
        settings.data_dir,
        settings.screenshots_dir,
        settings.backups_dir,
        settings.exports_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    # Дефолтные промпты кладутся в базу при первом старте (§33 п.18).
    # Ошибка тут не должна мешать приложению подняться: база может быть
    # ещё не мигрирована, и это чинится командой make migrate
    try:
        async with SessionMaker() as session:
            added = await seed_defaults(session)
            provider_added = await seed_default_provider(session)
        if added:
            log.info("Загружено промптов по умолчанию: %d", added)
        if provider_added:
            log.info("Заведён провайдер по умолчанию: локальная Ollama")
    except Exception as exc:
        log.warning("Промпты не загружены: %s. Выполните make migrate", exc)

    log.info("Бэкенд запущен, окружение %s", settings.app_env)
    yield
    log.info("Бэкенд остановлен")


app = FastAPI(
    title="HH JobPilot AI",
    description="Локальный помощник для поиска вакансий и откликов на hh.kz",
    version="0.1.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["Служебное"], summary="Проверка живости")
async def health() -> dict[str, str]:
    return {"status": "ok"}
