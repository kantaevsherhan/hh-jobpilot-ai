"""Собственные типы колонок."""

from typing import Any

from sqlalchemy import String, TypeDecorator
from sqlalchemy.engine import Dialect

from app.core.secrets import decrypt, encrypt


class EncryptedString(TypeDecorator[str]):
    """Строка, которая в базе лежит зашифрованной.

    Шифрование живёт в типе колонки, а не в сервисах: иначе рано или поздно
    появится место, которое запишет ключ мимо шифрования.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        return encrypt(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> str | None:
        return decrypt(value)
