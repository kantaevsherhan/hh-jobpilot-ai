"""Провайдер через CLI: claude -p / codex exec.

Официально поддерживаемый неинтерактивный режим, биллится по подписке.
Веб-интерфейсы chatgpt.com и claude.ai не автоматизируются никогда (§14).
"""

import asyncio
import json
from typing import Any

from app.core.errors import AppError
from app.llm.base import LLMProvider

# Готовые наборы аргументов, чтобы пользователю не приходилось их помнить
PRESETS: dict[str, list[str]] = {
    "claude": ["-p", "--output-format", "json"],
    "codex": ["exec"],
}


class CLIProvider(LLMProvider):
    type = "cli"

    async def complete(self, prompt: str, *, json_mode: bool = True) -> str:
        command = str(self.extra.get("command", "claude"))
        args = self.extra.get("args")
        argv = [command, *(args if isinstance(args, list) else PRESETS.get(command, []))]
        if self.model:
            argv += ["--model", self.model]

        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise AppError(
                "PROVIDER_UNAVAILABLE",
                f"Команда «{command}» не найдена. Установлен ли CLI и есть ли он в PATH?",
                technical_details=str(exc),
            ) from exc

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(prompt.encode()), timeout=self.timeout_sec
            )
        except TimeoutError as exc:
            process.kill()
            raise AppError(
                "PROVIDER_TIMEOUT",
                f"CLI «{command}» не ответил за {self.timeout_sec} сек",
            ) from exc

        if process.returncode != 0:
            raise AppError(
                "PROVIDER_UNAVAILABLE",
                f"CLI «{command}» завершился с ошибкой",
                technical_details=stderr.decode(errors="replace")[:2000],
            )

        return _unwrap(stdout.decode(errors="replace"))


def _unwrap(output: str) -> str:
    """claude --output-format json заворачивает ответ в конверт с метаданными."""
    try:
        envelope: Any = json.loads(output)
    except json.JSONDecodeError:
        return output
    if isinstance(envelope, dict) and "result" in envelope:
        return str(envelope["result"])
    return output
