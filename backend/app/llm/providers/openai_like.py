"""Провайдеры с OpenAI-совместимым HTTP API: openai и openrouter.

Одна реализация на два типа: у OpenRouter отличается только base_url.
Официальный SDK здесь не нужен — запрос ровно один.
"""

from typing import Any

import httpx

from app.core.errors import AppError
from app.llm.base import LLMProvider

DEFAULT_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


class OpenAILikeProvider(LLMProvider):
    type = "openai"

    async def complete(self, prompt: str, *, json_mode: bool = True) -> str:
        base = (self.base_url or DEFAULT_URLS.get(self.type, DEFAULT_URLS["openai"])).rstrip("/")
        payload: dict[str, Any] = {
            "model": self.model or "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as http:
                response = await http.post(
                    f"{base}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key or ''}"},
                )
                response.raise_for_status()
                body: dict[str, Any] = response.json()
        except httpx.TimeoutException as exc:
            raise AppError("PROVIDER_TIMEOUT", f"{self.name} не ответил вовремя") from exc
        except httpx.HTTPError as exc:
            raise AppError(
                "PROVIDER_UNAVAILABLE",
                f"{self.name} недоступен",
                technical_details=str(exc),
            ) from exc

        choices = body.get("choices") or []
        if not choices:
            raise AppError("INVALID_LLM_RESPONSE", f"{self.name} вернул пустой ответ")
        return str(choices[0]["message"]["content"])


class OpenRouterProvider(OpenAILikeProvider):
    type = "openrouter"
