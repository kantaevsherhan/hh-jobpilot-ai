"""Путь к базе и резервное копирование (§29).

`make backup` падал: путь к базе собирался в трёх местах по-разному,
и корень репозитория попадал в него дважды.
"""

import sqlite3
from pathlib import Path

import pytest

from app.core.config import ROOT_DIR, Settings
from app.core.errors import AppError
from app.storage.backup import create_backup


class TestПутьКБазе:
    def test_относительный_путь_считается_от_корня_репозитория(self) -> None:
        settings = Settings(database_url="sqlite+aiosqlite:///./data/jobpilot.db")

        assert settings.database_path == ROOT_DIR / "data" / "jobpilot.db"

    def test_абсолютный_путь_остаётся_абсолютным(self) -> None:
        # Именно здесь ломалось: корень приклеивался второй раз
        settings = Settings(database_url="sqlite+aiosqlite:////var/lib/jobpilot.db")

        assert settings.database_path == Path("/var/lib/jobpilot.db")

    def test_url_собирается_обратно_без_потерь(self) -> None:
        settings = Settings(database_url="sqlite+aiosqlite:///./data/jobpilot.db")

        assert settings.sqlalchemy_url.startswith("sqlite+aiosqlite:////")
        assert str(ROOT_DIR) in settings.sqlalchemy_url
        # Повторная сборка не должна удваивать путь
        assert settings.sqlalchemy_url.count(str(ROOT_DIR)) == 1

    def test_база_в_памяти_файла_не_имеет(self) -> None:
        assert Settings(database_url="sqlite+aiosqlite:///:memory:").database_path is None


class TestКопия:
    def test_копия_создаётся_и_читается(self, tmp_path: Path, monkeypatch) -> None:
        source = tmp_path / "app.db"
        with sqlite3.connect(source) as db:
            db.execute("CREATE TABLE vacancies (id INTEGER, title TEXT)")
            db.execute("INSERT INTO vacancies VALUES (1, 'Backend Developer')")

        monkeypatch.setattr(
            "app.storage.backup.settings",
            Settings(database_url=f"sqlite+aiosqlite:///{source}"),
        )

        result = create_backup(tmp_path / "backups")

        copy = Path(result["path"])
        assert copy.exists()
        with sqlite3.connect(copy) as db:
            assert db.execute("SELECT title FROM vacancies").fetchone()[0] == "Backend Developer"

    def test_копия_живой_базы_согласована(self, tmp_path: Path, monkeypatch) -> None:
        """Копирование файла во время записи давало бы битую копию:
        часть данных лежит в WAL-журнале."""
        source = tmp_path / "app.db"
        connection = sqlite3.connect(source)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE vacancies (id INTEGER, title TEXT)")
        connection.commit()
        connection.execute("INSERT INTO vacancies VALUES (1, 'Записано в WAL')")
        connection.commit()

        monkeypatch.setattr(
            "app.storage.backup.settings",
            Settings(database_url=f"sqlite+aiosqlite:///{source}"),
        )

        result = create_backup(tmp_path / "backups")
        connection.close()

        with sqlite3.connect(result["path"]) as db:
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert db.execute("SELECT title FROM vacancies").fetchone()[0] == "Записано в WAL"

    def test_отсутствующая_база_даёт_понятную_ошибку(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            "app.storage.backup.settings",
            Settings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'нет.db'}"),
        )

        with pytest.raises(AppError) as exc:
            create_backup(tmp_path / "backups")

        assert exc.value.error_code == "BACKUP_UNSUPPORTED"
