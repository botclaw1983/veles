from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    document_type: Mapped[str | None] = mapped_column(String(32))

    fund_name: Mapped[str] = mapped_column(Text, default="")
    fund_inn: Mapped[str] = mapped_column(String(12), default="")
    counterparty_name: Mapped[str] = mapped_column(Text, default="")
    counterparty_inn: Mapped[str] = mapped_column(String(12), default="")
    amount: Mapped[float | None] = mapped_column(Float)
    period_from: Mapped[datetime | None] = mapped_column(Date)
    period_to: Mapped[datetime | None] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text, default="")

    diadoc_box_id: Mapped[str | None] = mapped_column(String(128))
    diadoc_message_id: Mapped[str | None] = mapped_column(String(64))
    diadoc_entity_id: Mapped[str | None] = mapped_column(String(64))

    bank_client_status: Mapped[str] = mapped_column(String(32), default="not_uploaded")
    pdf_filename: Mapped[str | None] = mapped_column(Text)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    approvers: Mapped[list[DocumentApproverRow]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentApproverRow.sort_order",
    )


class DocumentApproverRow(Base):
    __tablename__ = "document_approvers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    document: Mapped[DocumentRow] = relationship(back_populates="approvers")


class DiadocSyncStateRow(Base):
    __tablename__ = "diadoc_sync_state"

    box_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    after_index_key: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
