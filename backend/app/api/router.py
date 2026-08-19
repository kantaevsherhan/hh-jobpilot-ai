"""Сборка всех роутеров под /api/v1."""

from fastapi import APIRouter

from app.api import browser, dictionaries, prompts, providers, resumes, settings

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(dictionaries.router)
api_router.include_router(resumes.router)
api_router.include_router(providers.router)
api_router.include_router(prompts.router)
api_router.include_router(settings.router)
api_router.include_router(browser.router)
