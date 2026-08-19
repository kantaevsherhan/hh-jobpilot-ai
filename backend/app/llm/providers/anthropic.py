"""Провайдер Anthropic через официальный SDK."""

from typing import Any

from app.core.errors import AppError
from app.llm.base import LLMProvider

DEFAULT_MODEL = "claude-haiku-4-5"


class AnthropicProvider(LLMProvider):
    type = "anthropic"

    async def complete(self, prompt: str, *, json_mode: bool = True) -> str:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:  # пакет опционален
            raise AppError("PROVIDER_UNAVAILABLE", "Пакет anthropic не установлен") from exc

        client = AsyncAnthropic(api_key=self.api_key, timeout=float(self.timeout_sec))
        # Модель охотнее отдаёт чистый JSON, если ответ начат за неё открывающей скобкой
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        if json_mode:
            messages.append({"role": "assistant", "content": "{"})

        try:
            response = await client.messages.create(
                model=self.model or DEFAULT_MODEL,
                max_tokens=int(self.extra.get("max_tokens", 4096)),
                temperature=self.temperature,
                messages=messages,  # type: ignore[arg-type]
            )
        except Exception as exc:
            raise AppError(
                "PROVIDER_UNAVAILABLE",
                "Anthropic недоступен или ключ неверный",
                technical_details=str(exc),
            ) from exc
        finally:
            await client.close()

        text = "".join(block.text for block in response.content if block.type == "text")
        return "{" + text if json_mode else text
