"""Клиент Diadoc API и загрузка входящих документов."""

from integrations.diadoc.client import DiadocClient
from integrations.diadoc.exceptions import DiadocApiError, DiadocConfigError, DiadocError
from integrations.diadoc.inbox import DiadocFetchResult, fetch_new_documents_from_diadoc, is_diadoc_configured

__all__ = [
    "DiadocApiError",
    "DiadocClient",
    "DiadocConfigError",
    "DiadocError",
    "DiadocFetchResult",
    "fetch_new_documents_from_diadoc",
    "is_diadoc_configured",
]
