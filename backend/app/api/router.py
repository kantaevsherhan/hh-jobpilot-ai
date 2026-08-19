"""Сборка всех роутеров под /api/v1."""

from fastapi import APIRouter

from app.api import (
    applications,
    backup,
    bot,
    browser,
    company_rules,
    dictionaries,
    letter_examples,
    letters,
    prompts,
    providers,
    resumes,
    runs,
    search_profiles,
    settings,
    stats,
    vacancies,
)

api_router = APIRouter(prefix="/api/v1")

for module in (
    dictionaries,
    bot,
    browser,
    resumes,
    vacancies,
    letters,
    applications,
    search_profiles,
    company_rules,
    letter_examples,
    providers,
    prompts,
    runs,
    stats,
    settings,
    backup,
):
    api_router.include_router(module.router)
