from __future__ import annotations


class DiadocError(Exception):
    """Базовая ошибка интеграции с Diadoc."""


class DiadocConfigError(DiadocError):
    """Не заданы обязательные параметры подключения."""


class DiadocApiError(DiadocError):
    """Ошибка HTTP-вызова Diadoc API."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
