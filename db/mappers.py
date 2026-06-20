from __future__ import annotations

from datetime import date, datetime

from db.models import DocumentApproverRow, DocumentRow
from models.document import (
    Approver,
    BankClientStatus,
    Document,
    DocumentFields,
    DocumentStatus,
    DocumentType,
    SpecDepStatus,
    normalize_inn,
)


def row_to_document(row: DocumentRow) -> Document:
    document_type = DocumentType(row.document_type) if row.document_type else None
    period_from = row.period_from.date() if isinstance(row.period_from, datetime) else row.period_from
    period_to = row.period_to.date() if isinstance(row.period_to, datetime) else row.period_to
    payment_date = (
        row.payment_date.date() if isinstance(row.payment_date, datetime) else row.payment_date
    )

    return Document(
        id=row.id,
        status=DocumentStatus(row.status),
        document_type=document_type,
        fields=DocumentFields(
            fund_name=row.fund_name,
        fund_inn=normalize_inn(row.fund_inn),
        zpif_name=row.zpif_name,
        counterparty_name=row.counterparty_name,
        counterparty_inn=normalize_inn(row.counterparty_inn),
            amount=row.amount,
            period_from=period_from,
            period_to=period_to,
            payment_date=payment_date,
            description=row.description,
        ),
        approvers=[
            Approver(name=approver.name, role=approver.role, approved=approver.approved)
            for approver in row.approvers
            if approver.section == "main"
        ],
        extra_approvers=[
            Approver(name=approver.name, role=approver.role, approved=approver.approved)
            for approver in row.approvers
            if approver.section == "extra"
        ],
        diadoc_box_id=row.diadoc_box_id,
        diadoc_message_id=row.diadoc_message_id,
        diadoc_entity_id=row.diadoc_entity_id,
        bank_client_status=BankClientStatus(row.bank_client_status),
        spec_dep_status=SpecDepStatus(row.spec_dep_status),
        real_estate_enabled=row.real_estate_enabled,
        pdf_filename=row.pdf_filename,
        received_at=row.received_at.replace(tzinfo=None) if row.received_at.tzinfo else row.received_at,
        updated_at=row.updated_at.replace(tzinfo=None) if row.updated_at.tzinfo else row.updated_at,
    )


def document_to_row(doc: Document) -> DocumentRow:
    row = DocumentRow(
        id=doc.id,
        status=doc.status.value,
        document_type=doc.document_type.value if doc.document_type else None,
        fund_name=doc.fields.fund_name,
        fund_inn=normalize_inn(doc.fields.fund_inn),
        zpif_name=doc.fields.zpif_name,
        counterparty_name=doc.fields.counterparty_name,
        counterparty_inn=normalize_inn(doc.fields.counterparty_inn),
        amount=doc.fields.amount,
        period_from=_as_date(doc.fields.period_from),
        period_to=_as_date(doc.fields.period_to),
        payment_date=_as_date(doc.fields.payment_date),
        description=doc.fields.description,
        diadoc_box_id=doc.diadoc_box_id,
        diadoc_message_id=doc.diadoc_message_id,
        diadoc_entity_id=doc.diadoc_entity_id,
        bank_client_status=doc.bank_client_status.value,
        spec_dep_status=doc.spec_dep_status.value,
        real_estate_enabled=doc.real_estate_enabled,
        pdf_filename=doc.pdf_filename,
        received_at=doc.received_at,
        updated_at=doc.updated_at,
    )
    row.approvers = _approver_rows(doc)
    return row


def _approver_rows(doc: Document) -> list[DocumentApproverRow]:
    rows: list[DocumentApproverRow] = []
    for index, approver in enumerate(doc.approvers):
        rows.append(
            DocumentApproverRow(
                name=approver.name,
                role=approver.role,
                approved=approver.approved,
                section="main",
                sort_order=index,
            )
        )
    for index, approver in enumerate(doc.extra_approvers):
        rows.append(
            DocumentApproverRow(
                name=approver.name,
                role=approver.role,
                approved=approver.approved,
                section="extra",
                sort_order=index,
            )
        )
    return rows


def update_row_from_document(row: DocumentRow, doc: Document) -> None:
    row.status = doc.status.value
    row.document_type = doc.document_type.value if doc.document_type else None
    row.fund_name = doc.fields.fund_name
    row.fund_inn = normalize_inn(doc.fields.fund_inn)
    row.zpif_name = doc.fields.zpif_name
    row.counterparty_name = doc.fields.counterparty_name
    row.counterparty_inn = normalize_inn(doc.fields.counterparty_inn)
    row.amount = doc.fields.amount
    row.period_from = _as_date(doc.fields.period_from)
    row.period_to = _as_date(doc.fields.period_to)
    row.payment_date = _as_date(doc.fields.payment_date)
    row.description = doc.fields.description
    row.diadoc_box_id = doc.diadoc_box_id
    row.diadoc_message_id = doc.diadoc_message_id
    row.diadoc_entity_id = doc.diadoc_entity_id
    row.bank_client_status = doc.bank_client_status.value
    row.spec_dep_status = doc.spec_dep_status.value
    row.real_estate_enabled = doc.real_estate_enabled
    row.pdf_filename = doc.pdf_filename
    row.updated_at = doc.updated_at

    row.approvers.clear()
    for approver_row in _approver_rows(doc):
        row.approvers.append(approver_row)


def _as_date(value: date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value
