"""Сборка всех роутеров под /api/v1."""

from fastapi import APIRouter

from app.api import dictionaries

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(dictionaries.router)
