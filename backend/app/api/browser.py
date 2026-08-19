"""Управление браузером и состоянием сессии HH (§9)."""

from typing import Any

from fastapi import APIRouter

from app.browser.manager import browser

router = APIRouter(prefix="/browser", tags=["Браузер"])


@router.get("/status", summary="Состояние браузера и сессии")
async def status() -> dict[str, Any]:
    return await browser.status()


@router.post("/start", summary="Запустить браузер")
async def start() -> dict[str, Any]:
    await browser.start()
    return await browser.status()


@router.post("/check-auth", summary="Проверить, выполнен ли вход")
async def check_auth() -> dict[str, Any]:
    await browser.check_auth()
    return await browser.status()


@router.post("/restart", summary="Перезапустить браузер")
async def restart() -> dict[str, Any]:
    await browser.restart()
    return await browser.status()


@router.post("/close", summary="Закрыть браузер")
async def close() -> dict[str, Any]:
    await browser.stop()
    return await browser.status()
