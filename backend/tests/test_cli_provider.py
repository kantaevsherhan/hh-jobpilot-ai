"""CLI-провайдеры: claude -p и codex exec без запуска самих CLI."""

import json
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.errors import AppError
from app.llm.providers import cli


def test_claude_без_инструментов_с_моделью_и_усилием(tmp_path: Path) -> None:
    argv = cli.build_argv(
        "claude", "claude.exe", model="haiku", effort="low", output_file=tmp_path / "a"
    )

    assert argv[:2] == ["claude.exe", "-p"]
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--model") + 1] == "haiku"
    assert argv[argv.index("--effort") + 1] == "low"


def test_claude_без_модели_берёт_настройки_cli(tmp_path: Path) -> None:
    argv = cli.build_argv("claude", "claude", model=None, effort=None, output_file=tmp_path / "a")

    assert "--model" not in argv
    assert "--effort" not in argv


def test_codex_только_чтение_и_ответ_в_файл(tmp_path: Path) -> None:
    out = tmp_path / "answer.txt"

    argv = cli.build_argv("codex", "codex.exe", model="gpt-x", effort="medium", output_file=out)

    assert argv[:2] == ["codex.exe", "exec"]
    # Конфиг пользователя написан под его машину и ломает запуск в контейнере
    assert "--ignore-user-config" in argv
    assert argv[argv.index("--sandbox") + 1] == "read-only"
    assert argv[argv.index("-o") + 1] == str(out)
    assert 'model_reasoning_effort="medium"' in argv
    # Промпт из stdin
    assert argv[-1] == "-"


def test_явный_путь_к_cli_используется_как_есть(tmp_path: Path) -> None:
    exe = tmp_path / "claude.exe"
    exe.write_text("")

    assert cli.find_executable("claude", str(exe)) == str(exe)
    assert cli.find_executable("claude", str(tmp_path / "нет.exe")) is None


def test_модели_codex_читаются_из_его_кэша(tmp_path: Path) -> None:
    cache = tmp_path / "models_cache.json"
    cache.write_text(
        json.dumps(
            {
                "models": [
                    {"slug": "hidden", "visibility": "hide", "priority": 0},
                    {
                        "slug": "gpt-b",
                        "display_name": "GPT B",
                        "priority": 2,
                        "default_reasoning_level": "low",
                        "supported_reasoning_levels": [{"effort": "low"}, {"effort": "high"}],
                    },
                    {"slug": "gpt-a", "priority": 1},
                ]
            }
        ),
        encoding="utf-8",
    )

    models = cli.load_codex_models(cache)

    assert [m.id for m in models] == ["", "gpt-a", "gpt-b"]
    assert models[2].efforts == ["low", "high"]
    assert models[2].default_effort == "low"


def test_без_кэша_codex_остаётся_модель_по_умолчанию(tmp_path: Path) -> None:
    models = cli.load_codex_models(tmp_path / "нет.json")

    assert [m.id for m in models] == [""]


def test_причина_ошибки_codex_достаётся_из_вывода() -> None:
    output = "OpenAI Codex v0.1\nmodel: gpt-x\nERROR: You've hit your usage limit.\n"

    assert cli.cli_error_reason(output) == "You've hit your usage limit."
    assert cli.cli_error_reason("просто упал") is None


def test_конверт_claude_разворачивается() -> None:
    assert cli._unwrap(json.dumps({"result": '{"ok": true}'})) == '{"ok": true}'


def test_ошибка_в_конверте_claude_не_выдаётся_за_ответ() -> None:
    with pytest.raises(AppError):
        cli._unwrap(json.dumps({"result": "Not logged in", "is_error": True}))


async def test_ненайденный_cli_это_понятная_ошибка(tmp_path: Path) -> None:
    provider = cli.CLIProvider(name="cli", extra={"command": "claude", "path": str(tmp_path / "x")})

    with pytest.raises(AppError) as exc:
        await provider.complete("промпт")

    assert exc.value.error_code == "PROVIDER_UNAVAILABLE"


async def test_каталог_отдаёт_оба_cli(client: AsyncClient) -> None:
    response = await client.get("/api/v1/providers/cli/catalog")

    assert response.status_code == 200
    assert [tool["command"] for tool in response.json()] == ["claude", "codex"]
