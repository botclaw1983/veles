from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from db.engine import get_session
from db.mappers import document_to_row, row_to_document, update_row_from_document
from db.models import DocumentRow
from models.document import Document


def list_documents() -> list[Document]:
    with get_session() as session:
        rows = session.scalars(
            select(DocumentRow)
            .options(joinedload(DocumentRow.approvers))
            .order_by(DocumentRow.received_at.desc())
        ).unique().all()
        return [row_to_document(row) for row in rows]


def get_document(document_id: str) -> Document | None:
    with get_session() as session:
        row = session.scalar(
            select(DocumentRow)
            .options(joinedload(DocumentRow.approvers))
            .where(DocumentRow.id == document_id)
        )
        if row is None:
            return None
        return row_to_document(row)


def add_documents(documents: list[Document]) -> None:
    if not documents:
        return
    with get_session() as session:
        for doc in documents:
            session.add(document_to_row(doc))


def save_document(doc: Document) -> None:
    doc.touch()
    with get_session() as session:
        row = session.get(DocumentRow, doc.id)
        if row is None:
            session.add(document_to_row(doc))
            return
        update_row_from_document(row, doc)
