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

    @property
    def approval_label(self) -> str:
        if self in (DocumentStatus.APPROVED, DocumentStatus.SENT_TO_AVANKOR):
            return "Согласован"
        if self == DocumentStatus.ON_APPROVAL:
            return "Ожидается согласование"
        return "Не согласован"


class ApprovalPhase(str, Enum):
    NOT_APPROVED = "not_approved"
    PENDING = "pending"
    APPROVED = "approved"


@dataclass
class Approver:
    name: str
    role: str = ""
    approved: bool = False


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
    approvers: list[Approver] = field(default_factory=list)

    diadoc_box_id: str | None = None
    diadoc_message_id: str | None = None
    diadoc_entity_id: str | None = None

    pdf_filename: str | None = None
    received_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def touch(self) -> None:
        self.updated_at = datetime.now()

    @property
    def approval_phase(self) -> ApprovalPhase:
        if self.status in (DocumentStatus.APPROVED, DocumentStatus.SENT_TO_AVANKOR):
            return ApprovalPhase.APPROVED
        if self.status == DocumentStatus.ON_APPROVAL:
            return ApprovalPhase.PENDING
        return ApprovalPhase.NOT_APPROVED

    def ensure_approvers(self, defaults: list[tuple[str, str]]) -> None:
        if self.approvers:
            return
        self.approvers = [Approver(name=name, role=role) for name, role in defaults]

    def is_fully_approved(self) -> bool:
        return bool(self.approvers) and all(a.approved for a in self.approvers)

    @property
    def all_approvers_approved(self) -> bool:
        return self.is_fully_approved()

    def reset_approvals(self) -> None:
        for approver in self.approvers:
            approver.approved = False

    def approve_approver(self, index: int) -> None:
        if index < 0 or index >= len(self.approvers):
            return
        self.approvers[index].approved = True
        if self.is_fully_approved():
            self.status = DocumentStatus.APPROVED
