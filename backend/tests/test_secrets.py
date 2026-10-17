"""Шифрование ключей внешних провайдеров (§29).

Задача скромная и явная: файл базы и её резервная копия не должны
раскрывать ключи от Anthropic, OpenAI и OpenRouter.
"""

import os
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import secrets
from app.storage.models import LLMProvider

KEY = "sk-ant-api03-СЕКРЕТНЫЙ-КЛЮЧ-1234567890"


@pytest.fixture(autouse=True)
def key_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "secret.key"
    monkeypatch.setattr(secrets, "KEY_PATH", path)
    return path


class TestШифрование:
    def test_значение_шифруется_и_расшифровывается(self) -> None:
        encrypted = secrets.encrypt(KEY)

        assert encrypted is not None
        assert encrypted.startswith("enc:")
        assert KEY not in encrypted
        assert secrets.decrypt(encrypted) == KEY

    def test_одно_и_то_же_значение_шифруется_по_разному(self) -> None:
        # Иначе по одинаковым шифротекстам видно, что ключи совпадают
        assert secrets.encrypt(KEY) != secrets.encrypt(KEY)

    def test_пустое_значение_не_трогаем(self) -> None:
        assert secrets.encrypt(None) is None
        assert secrets.encrypt("") == ""
        assert secrets.decrypt(None) is None

    def test_повторное_шифрование_не_наслаивается(self) -> None:
        once = secrets.encrypt(KEY)

        assert secrets.encrypt(once) == once

    def test_ключ_записанный_до_шифрования_читается_как_есть(self) -> None:
        # В базе могут лежать ключи из версии без шифрования,
        # и ронять из-за них приложение нельзя
        assert secrets.decrypt(KEY) == KEY

    def test_потерянный_файл_ключа_не_роняет_приложение(self, key_file: Path) -> None:
        encrypted = secrets.encrypt(KEY)
        key_file.unlink()

        assert secrets.decrypt(encrypted) is None

    @pytest.mark.skipif(os.name == "nt", reason="Windows использует ACL вместо POSIX-прав")
    def test_файл_ключа_недоступен_другим_пользователям(self, key_file: Path) -> None:
        secrets.encrypt(KEY)

        assert key_file.exists()
        assert oct(key_file.stat().st_mode)[-3:] == "600"

    def test_ключ_лежит_вне_каталога_данных(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Резервная копия базы лежит в data/ и не должна уносить ключ с собой."""
        import importlib

        from app.core.config import settings

        monkeypatch.delenv("JOBPILOT_KEY_FILE", raising=False)
        default = importlib.reload(secrets).KEY_PATH

        assert settings.data_dir not in default.parents
        assert settings.data_dir != default.parent


class TestХранение:
    async def test_в_базе_лежит_шифротекст_а_не_ключ(
        self, session: AsyncSession, tmp_path: Path
    ) -> None:
        session.add(LLMProvider(name="Anthropic", type="anthropic", api_key=KEY))
        await session.commit()

        # Читаем через модель — ключ расшифрован
        provider = await session.get(LLMProvider, 1)
        assert provider is not None
        assert provider.api_key == KEY

        # Читаем сырое значение в обход модели — там шифротекст
        result = await session.execute(text("SELECT api_key FROM llm_providers WHERE id = 1"))
        stored = result.scalar()
        assert stored is not None
        assert stored.startswith("enc:")
        assert KEY not in stored

    async def test_локальному_провайдеру_ключ_не_нужен(self, session: AsyncSession) -> None:
        session.add(LLMProvider(name="Ollama", type="ollama"))
        await session.commit()

        provider = await session.get(LLMProvider, 1)
        assert provider is not None
        assert provider.api_key is None


def test_копия_базы_не_содержит_ключ_в_открытом_виде(tmp_path: Path) -> None:
    """Смысл всей затеи: утёкшая копия базы не раскрывает ключи."""
    database = tmp_path / "app.db"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE llm_providers (id INTEGER, api_key TEXT)")
        db.execute("INSERT INTO llm_providers VALUES (1, ?)", (secrets.encrypt(KEY),))

    assert KEY.encode() not in database.read_bytes()
