"""Локальная модель через Ollama.

Адрес, модель и num_ctx берутся из строки провайдера в БД и правятся
из UI. Константы ниже — только значения для первой строки на пустой базе.
"""

import time
from typing import Any

import httpx

from app.core.errors import AppError
from app.llm.base import LLMProvider

DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:4b-instruct"
# Дефолт Ollama 4096 молча обрежет промпт, и модель перестанет видеть
# половину вакансии (§2), поэтому num_ctx выставляется всегда явно
DEFAULT_NUM_CTX = 8192


class OllamaProvider(LLMProvider):
    type = "ollama"

    async def complete(self, prompt: str, *, json_mode: bool = True) -> str:
        url = (self.base_url or DEFAULT_URL).rstrip("/") + "/api/generate"
        options: dict[str, Any] = {
            "temperature": self.temperature,
            "num_ctx": int(self.extra.get("num_ctx", DEFAULT_NUM_CTX)),
        }
        payload: dict[str, Any] = {
            "model": self.model or DEFAULT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": options,
            "keep_alive": self.extra.get("keep_alive", "30m"),
        }
        if json_mode:
            payload["format"] = "json"

        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as http:
                response = await http.post(url, json=payload)
                response.raise_for_status()
                body: dict[str, Any] = response.json()
        except httpx.TimeoutException as exc:
            raise AppError(
                "PROVIDER_TIMEOUT",
                f"Ollama не ответила за {self.timeout_sec} сек",
                technical_details=str(exc),
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                "PROVIDER_UNAVAILABLE",
                "Ollama недоступна. Запущен ли ollama serve?",
                technical_details=str(exc),
            ) from exc

        self.last_elapsed = time.monotonic() - started
        return str(body.get("response", ""))
