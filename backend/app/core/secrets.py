"""Шифрование ключей внешних провайдеров.

Приложение локальное и однопользовательское, поэтому задача скромная:
чтобы файл базы и её резервная копия не раскрывали ключи от Anthropic,
OpenAI и OpenRouter. Ключ шифрования лежит вне репозитория и вне data/,
так что копия базы его с собой не уносит.

От пользователя, у которого есть доступ к домашнему каталогу, это не
защищает и защищать не может — такой цели тут нет.
"""

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.logging import get_logger

log = get_logger(__name__)

PREFIX = "enc:"

# Каталог настроек пользователя, а не проекта: резервная копия базы лежит
# в data/ и не должна содержать ключ от самой себя
KEY_PATH = Path(
    os.environ.get("JOBPILOT_KEY_FILE")
    or Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    / "hh-jobpilot"
    / "secret.key"
)


def _load_key(path: Path | None = None) -> bytes:
    key_path = path or KEY_PATH
    if key_path.exists():
        return key_path.read_bytes().strip()

    key_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    key_path.chmod(0o600)
    log.info("Создан ключ шифрования: %s", key_path)
    return key


def encrypt(value: str | None, *, key_path: Path | None = None) -> str | None:
    """Зашифровать значение. Пустое остаётся пустым."""
    if not value:
        return value
    if value.startswith(PREFIX):
        return value
    token = Fernet(_load_key(key_path)).encrypt(value.encode())
    return PREFIX + token.decode()


def decrypt(value: str | None, *, key_path: Path | None = None) -> str | None:
    """Расшифровать значение.

    Значение без префикса возвращается как есть: в базе могут лежать ключи,
    записанные до появления шифрования, и ронять из-за них приложение нельзя.
    Такой ключ зашифруется при первом же сохранении провайдера.
    """
    if not value or not value.startswith(PREFIX):
        return value
    try:
        return Fernet(_load_key(key_path)).decrypt(value[len(PREFIX) :].encode()).decode()
    except (InvalidToken, ValueError):
        log.warning("Ключ провайдера не расшифровывается — потерян файл ключа?")
        return None
