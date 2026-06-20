from __future__ import annotations

from config.reference_data import EXTRA_APPROVER_COUNT
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
import re
from uuid import uuid4


def normalize_inn(value: str | None) -> str:
    """ИНН юрлица — 10 цифр, физлица — 12. Остальное отбрасывается."""
    if not value:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if not digits or not digits.strip("0"):
        return ""
    if len(digits) in (10, 12):
        return digits
    return ""


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
            return "На согласовании"
        if self == DocumentStatus.REJECTED:
            return "Отклонён"
        return "Не обработан"


class BankClientStatus(str, Enum):
    NOT_UPLOADED = "not_uploaded"
    UPLOADED = "uploaded"
    PAID = "paid"

    @property
    def label(self) -> str:
        labels = {
            BankClientStatus.NOT_UPLOADED: "—",
            BankClientStatus.UPLOADED: "Загружено",
            BankClientStatus.PAID: "Оплачено",
        }
        return labels[self]


class SpecDepStatus(str, Enum):
    NOT_SENT = "not_sent"
    SENT = "sent"

    @property
    def label(self) -> str:
        labels = {
            SpecDepStatus.NOT_SENT: "—",
            SpecDepStatus.SENT: "Отправлено",
        }
        return labels[self]


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
    zpif_name: str = ""
    counterparty_name: str = ""
    counterparty_inn: str = ""
    amount: float | None = None
    period_from: date | None = None
    period_to: date | None = None
    payment_date: date | None = None
    description: str = ""


@dataclass
class Document:
    id: str = field(default_factory=lambda: str(uuid4()))
    status: DocumentStatus = DocumentStatus.NEW
    document_type: DocumentType | None = None
    fields: DocumentFields = field(default_factory=DocumentFields)
    approvers: list[Approver] = field(default_factory=list)
    extra_approvers: list[Approver] = field(default_factory=list)

    diadoc_box_id: str | None = None
    diadoc_message_id: str | None = None
    diadoc_entity_id: str | None = None

    bank_client_status: BankClientStatus = BankClientStatus.NOT_UPLOADED
    spec_dep_status: SpecDepStatus = SpecDepStatus.NOT_SENT
    real_estate_enabled: bool = False

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

    def ensure_approvers(
        self,
        defaults: list[tuple[str, str]],
        *,
        extra_defaults: list[tuple[str, str]] | None = None,
    ) -> None:
        self._sync_approver_list(self.approvers, defaults)
        if extra_defaults is not None:
            self._sync_approver_list(self.extra_approvers, extra_defaults)

    @staticmethod
    def _sync_approver_list(
        current: list[Approver],
        defaults: list[tuple[str, str]],
    ) -> None:
        if not defaults:
            current.clear()
            return
        approved_by_name = {approver.name: approver.approved for approver in current}
        if len(current) == len(defaults) and all(
            current[index].name == name and current[index].role == role
            for index, (name, role) in enumerate(defaults)
        ):
            return
        current[:] = [
            Approver(name=name, role=role, approved=approved_by_name.get(name, False))
            for name, role in defaults
        ]

    def is_fully_approved(self) -> bool:
        if not self.approvers or not all(a.approved for a in self.approvers):
            return False
        if self.real_estate_enabled:
            extra = self.extra_approvers[:EXTRA_APPROVER_COUNT]
            return bool(extra) and all(a.approved for a in extra)
        return True

    @property
    def all_approvers_approved(self) -> bool:
        return self.is_fully_approved()

    def reset_approvals(self) -> None:
        for approver in self.approvers:
            approver.approved = False
        for approver in self.extra_approvers:
            approver.approved = False

    def approve_approver(self, index: int) -> None:
        if index < 0 or index >= len(self.approvers):
            return
        self.approvers[index].approved = True
        if self.is_fully_approved():
            self.status = DocumentStatus.APPROVED

    def approve_extra_approver(self, index: int) -> None:
        if index < 0 or index >= len(self.extra_approvers):
            return
        self.extra_approvers[index].approved = True
        if self.is_fully_approved():
            self.status = DocumentStatus.APPROVED
