"""Структурные ошибки приложения (§25)."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.enums import ERROR_CODE_LABELS, ErrorCode


class AppError(Exception):
    """Ошибка с кодом и человекочитаемым сообщением.

    Всё, что показывается пользователю, обязано приходить отсюда:
    голый текст исключения на русском в UI не выводится.
    """

    status_code = 400

    def __init__(
        self,
        error_code: ErrorCode | str,
        human_message: str | None = None,
        *,
        step: str | None = None,
        technical_details: str | None = None,
        recoverable: bool = True,
        screenshot_path: str | None = None,
    ) -> None:
        self.error_code = str(error_code)
        self.human_message = human_message or ERROR_CODE_LABELS.get(
            self.error_code, "Неизвестная ошибка"
        )
        self.step = step
        self.technical_details = technical_details
        self.recoverable = recoverable
        self.screenshot_path = screenshot_path
        super().__init__(self.human_message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "human_message": self.human_message,
            "step": self.step,
            "technical_details": self.technical_details,
            "recoverable": self.recoverable,
            "screenshot_path": self.screenshot_path,
        }


class NotFoundError(AppError):
    status_code = 404

    def __init__(self, what: str) -> None:
        super().__init__("NOT_FOUND", f"{what} не найдено", recoverable=False)


class ConflictError(AppError):
    status_code = 409


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.to_dict()})
