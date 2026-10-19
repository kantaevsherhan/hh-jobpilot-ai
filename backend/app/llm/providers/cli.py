"""Провайдер через CLI: claude -p / codex exec.

Официально поддерживаемый неинтерактивный режим, биллится по подписке.
Веб-интерфейсы chatgpt.com и claude.ai не автоматизируются никогда (§14).
"""

import asyncio
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.core.errors import AppError
from app.llm.base import LLMProvider

CLAUDE = "claude"
CODEX = "codex"

# Уровни из `claude --help`; у Codex они свои у каждой модели и берутся из его кэша
CLAUDE_EFFORTS = ["low", "medium", "high", "xhigh", "max"]
_EFFORT_ORDER = {effort: i for i, effort in enumerate(["minimal", *CLAUDE_EFFORTS, "ultra"])}

# Подсказки для выпадающего списка, а не ограничение: поле модели принимает любое имя,
# которое понимает установленная версия CLI
CLAUDE_MODELS = [
    ("", "По умолчанию CLI", "Модель из настроек Claude Code"),
    ("fable", "Fable — последняя", "Самая сильная, дороже по лимитам подписки"),
    ("opus", "Opus — последняя", "Сильная модель для писем и проверки фактов"),
    ("sonnet", "Sonnet — последняя", "Баланс скорости и качества"),
    ("haiku", "Haiku — последняя", "Быстрая и дешёвая, хватает для анализа вакансий"),
]


@dataclass(slots=True)
class CLIModel:
    id: str
    label: str
    description: str = ""
    efforts: list[str] = field(default_factory=list)
    default_effort: str | None = None


@dataclass(slots=True)
class CLITool:
    command: str
    label: str
    path: str | None
    models: list[CLIModel]
    efforts: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _known_locations(command: str) -> list[Path]:
    """Куда ставят CLI официальные установщики.

    Бэкенд часто запущен не из того окна, где пользователь ставил CLI, и PATH
    у него свой, поэтому одного shutil.which мало.
    """
    home = Path.home()
    appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    places = [
        home / ".local" / "bin" / f"{command}.exe",
        home / ".local" / "bin" / command,
        appdata / "npm" / f"{command}.cmd",
        Path("/usr/local/bin") / command,
        Path("/opt/homebrew/bin") / command,
    ]
    if command == CODEX:
        # Приложение Codex кладёт CLI в каталог с хэшем версии — берём самый свежий
        bundled = sorted(
            (local / "OpenAI" / "Codex" / "bin").glob("*/codex.exe"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        places = [*places, *bundled]
    return places


def find_executable(command: str, explicit: str | None = None) -> str | None:
    if explicit:
        return explicit if Path(explicit).is_file() else None
    found = shutil.which(command)
    if found:
        return found
    return next((str(p) for p in _known_locations(command) if p.is_file()), None)


def _codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def load_codex_models(cache_file: Path | None = None) -> list[CLIModel]:
    """Модели Codex из его собственного кэша: список меняется вместе с CLI,
    и держать копию в коде значит отставать от него."""
    path = cache_file or _codex_home() / "models_cache.json"
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [CLIModel("", "По умолчанию CLI", "Модель из ~/.codex/config.toml")]

    models = [CLIModel("", "По умолчанию CLI", "Модель из ~/.codex/config.toml")]
    raw_models = data.get("models", []) if isinstance(data, dict) else []
    for item in sorted(raw_models, key=lambda m: m.get("priority", 999)):
        if not isinstance(item, dict) or item.get("visibility", "list") != "list":
            continue
        efforts = [
            str(level["effort"])
            for level in item.get("supported_reasoning_levels", [])
            if isinstance(level, dict) and "effort" in level
        ]
        models.append(
            CLIModel(
                id=str(item["slug"]),
                label=str(item.get("display_name") or item["slug"]),
                description=str(item.get("description", "")),
                efforts=efforts,
                default_effort=item.get("default_reasoning_level"),
            )
        )
    return models


def catalog() -> list[CLITool]:
    """Что установлено и из чего выбирать — для формы провайдера."""
    claude_models = [
        CLIModel(model_id, label, hint, CLAUDE_EFFORTS) for model_id, label, hint in CLAUDE_MODELS
    ]
    codex_models = load_codex_models()
    # Порядок по возрастанию «глубины», чтобы в списке не было low после max
    codex_efforts = sorted(
        {e for m in codex_models for e in m.efforts}, key=lambda e: (_EFFORT_ORDER.get(e, 99), e)
    )
    return [
        CLITool(CLAUDE, "Claude Code CLI", find_executable(CLAUDE), claude_models, CLAUDE_EFFORTS),
        CLITool(CODEX, "Codex CLI", find_executable(CODEX), codex_models, codex_efforts),
    ]


def build_argv(
    command: str, executable: str, *, model: str | None, effort: str | None, output_file: Path
) -> list[str]:
    """Аргументы для разового текстового ответа.

    Инструменты отключены: модели нужен только текст промпта, а не доступ к
    файлам и командам машины. Промпт идёт через stdin — в аргументах
    командной строки Windows он упирается в лимит длины.
    """
    if command == CLAUDE:
        argv = [executable, "-p", "--output-format", "json", "--no-session-persistence"]
        argv += ["--tools", ""]
        if model:
            argv += ["--model", model]
        if effort:
            argv += ["--effort", effort]
        return argv

    if command == CODEX:
        argv = [executable, "exec", "--skip-git-repo-check", "--ephemeral"]
        argv += ["--sandbox", "read-only", "--color", "never", "-o", str(output_file)]
        if model:
            argv += ["--model", model]
        if effort:
            argv += ["-c", f'model_reasoning_effort="{effort}"']
        return [*argv, "-"]

    # Произвольная команда: пользователь сам знает её флаги
    argv = [executable]
    if model:
        argv += ["--model", model]
    return argv


class CLIProvider(LLMProvider):
    type = "cli"

    async def complete(self, prompt: str, *, json_mode: bool = True) -> str:
        command = str(self.extra.get("command") or CLAUDE)
        explicit_path = self.extra.get("path")
        executable = find_executable(command, str(explicit_path) if explicit_path else None)
        if executable is None:
            raise AppError(
                "PROVIDER_UNAVAILABLE",
                f"Команда «{command}» не найдена. Установите CLI или укажите путь к нему",
            )
        effort = self.extra.get("effort")

        # Пустая временная папка вместо каталога проекта: иначе CLI подхватит
        # CLAUDE.md / AGENTS.md репозитория и примет их за инструкции к ответу
        with tempfile.TemporaryDirectory(prefix="jobpilot-cli-") as workdir:
            output_file = Path(workdir) / "answer.txt"
            args = self.extra.get("args")
            argv = (
                [executable, *map(str, args)]
                if isinstance(args, list)
                else build_argv(
                    command,
                    executable,
                    model=self.model,
                    effort=str(effort) if effort else None,
                    output_file=output_file,
                )
            )
            stdout, stderr = await self._run(command, argv, prompt, workdir)
            if output_file.is_file():
                return output_file.read_text(encoding="utf-8", errors="replace")
        return _unwrap(stdout)

    async def _run(
        self, command: str, argv: list[str], prompt: str, workdir: str
    ) -> tuple[str, str]:
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=workdir,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise AppError(
                "PROVIDER_UNAVAILABLE",
                f"Не удалось запустить «{command}»",
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

        out = stdout.decode(errors="replace")
        err = stderr.decode(errors="replace")
        if process.returncode != 0:
            reason = cli_error_reason(err or out)
            raise AppError(
                "PROVIDER_UNAVAILABLE",
                f"CLI «{command}»: {reason}" if reason else f"CLI «{command}» завершился с ошибкой",
                technical_details=(err or out)[-2000:],
            )
        return out, err


def cli_error_reason(output: str) -> str | None:
    """Последняя строка «ERROR: …» — в ней CLI пишет настоящую причину
    (лимит подписки, нет входа), а выше идёт служебная шапка сессии."""
    errors = [
        line.split(":", 1)[1].strip()
        for line in output.splitlines()
        if line.strip().upper().startswith("ERROR:")
    ]
    return errors[-1] if errors else None


def _unwrap(output: str) -> str:
    """claude --output-format json заворачивает ответ в конверт с метаданными."""
    try:
        envelope: Any = json.loads(output)
    except json.JSONDecodeError:
        return output
    if isinstance(envelope, dict) and "result" in envelope:
        if envelope.get("is_error"):
            raise AppError(
                "PROVIDER_UNAVAILABLE",
                "Claude CLI вернул ошибку",
                technical_details=str(envelope["result"])[:2000],
            )
        return str(envelope["result"])
    return output
