from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from db.engine import get_session
from db.models import DiadocSyncStateRow


def load_sync_state() -> dict[str, str]:
    with get_session() as session:
        rows = session.scalars(select(DiadocSyncStateRow)).all()
        return {row.box_id: row.after_index_key for row in rows}


def save_sync_state(state: dict[str, str]) -> None:
    now = datetime.now(UTC)
    with get_session() as session:
        for box_id, after_index_key in state.items():
            row = session.get(DiadocSyncStateRow, box_id)
            if row is None:
                session.add(
                    DiadocSyncStateRow(
                        box_id=box_id,
                        after_index_key=after_index_key,
                        updated_at=now,
                    )
                )
            else:
                row.after_index_key = after_index_key
                row.updated_at = now
