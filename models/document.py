from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from uuid import uuid4


class DocumentType(str, Enum):
    INVOICE = "invoice"
    ACT = "act"
    UTD = "utd"
    TURNOVER = "turnover"

    @property
    def label(self) -> str:
        labels = {
            DocumentType.INVOICE: "Счёт",
            DocumentType.ACT: "Акт",
            DocumentType.UTD: "УПД",
            DocumentType.TURNOVER: "Товарооборот",
        }
        return labels[self]


class DocumentStatus(str, Enum):
    NEW = "new"
    ON_APPROVAL = "on_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT_TO_AVANKOR = "sent_to_avankor"

    @property
    def label(self) -> str:
        labels = {
            DocumentStatus.NEW: "Новый",
            DocumentStatus.ON_APPROVAL: "На согласовании",
            DocumentStatus.APPROVED: "Согласован",
            DocumentStatus.REJECTED: "Отклонён",
            DocumentStatus.SENT_TO_AVANKOR: "Отправлен в Аванкор",
        }
        return labels[self]


@dataclass
class DocumentFields:
    fund_name: str = ""
    fund_inn: str = ""
    counterparty_name: str = ""
    counterparty_inn: str = ""
    amount: float | None = None
    period_from: date | None = None
    period_to: date | None = None
    description: str = ""


@dataclass
class Document:
    id: str = field(default_factory=lambda: str(uuid4()))
    status: DocumentStatus = DocumentStatus.NEW
    document_type: DocumentType | None = None
    fields: DocumentFields = field(default_factory=DocumentFields)

    diadoc_box_id: str | None = None
    diadoc_message_id: str | None = None
    diadoc_entity_id: str | None = None

    pdf_filename: str | None = None
    received_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def touch(self) -> None:
        self.updated_at = datetime.now()
