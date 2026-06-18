from __future__ import annotations

from sqlalchemy import inspect, text

from db.engine import engine
from db.models import Base


def _migrate_schema() -> None:
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("documents")}
    if "spec_dep_status" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE documents "
                    "ADD COLUMN spec_dep_status VARCHAR(32) DEFAULT 'not_sent' NOT NULL"
                )
            )
    if "real_estate_enabled" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE documents "
                    "ADD COLUMN real_estate_enabled BOOLEAN DEFAULT FALSE NOT NULL"
                )
            )
    if "zpif_name" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE documents ADD COLUMN zpif_name TEXT DEFAULT '' NOT NULL")
            )
    if "payment_date" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE documents ADD COLUMN payment_date DATE"))

    if "document_approvers" in inspector.get_table_names():
        approver_columns = {
            column["name"] for column in inspector.get_columns("document_approvers")
        }
        if "section" not in approver_columns:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE document_approvers "
                        "ADD COLUMN section VARCHAR(16) DEFAULT 'main' NOT NULL"
                    )
                )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_schema()
