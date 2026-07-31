"""Manual publish queue for semi-automated Instagram scheduling.

States:
    READY_FOR_REVIEW → APPROVED → READY_FOR_MANUAL_SCHEDULING →
    MANUALLY_SCHEDULED → PUBLISHED_CONFIRMED | CANCELLED
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..utils.helpers import ensure_dir, project_root
from .errors import QueueError


class ManualQueueState:
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    READY_FOR_MANUAL_SCHEDULING = "READY_FOR_MANUAL_SCHEDULING"
    MANUALLY_SCHEDULED = "MANUALLY_SCHEDULED"
    PUBLISHED_CONFIRMED = "PUBLISHED_CONFIRMED"
    CANCELLED = "CANCELLED"


_VALID_MANUAL_TRANSITIONS: dict[str, set[str]] = {
    ManualQueueState.READY_FOR_REVIEW: {ManualQueueState.APPROVED, ManualQueueState.CANCELLED},
    ManualQueueState.APPROVED: {
        ManualQueueState.READY_FOR_MANUAL_SCHEDULING,
        ManualQueueState.CANCELLED,
    },
    ManualQueueState.READY_FOR_MANUAL_SCHEDULING: {
        ManualQueueState.MANUALLY_SCHEDULED,
        ManualQueueState.CANCELLED,
    },
    ManualQueueState.MANUALLY_SCHEDULED: {
        ManualQueueState.PUBLISHED_CONFIRMED,
        ManualQueueState.CANCELLED,
    },
    ManualQueueState.PUBLISHED_CONFIRMED: set(),
    ManualQueueState.CANCELLED: set(),
}


class ManualQueue:
    """SQLite-backed queue for manual Instagram publishing workflow."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = project_root() / "data" / "manual-queue.db"
        self.db_path = Path(db_path)
        ensure_dir(self.db_path.parent)
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS manual_queue (
                brief_id TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'READY_FOR_REVIEW',
                approval_id TEXT,
                image_checksum TEXT,
                caption_checksum TEXT,
                bundle_path TEXT,
                permalink TEXT,
                scheduled_at TEXT,
                published_at TEXT,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_state ON manual_queue(state);
        """)
        conn.commit()

    def add(
        self,
        brief_id: str,
        approval_id: str = "",
        image_checksum: str = "",
        caption_checksum: str = "",
        bundle_path: str = "",
    ) -> None:
        """Add a brief to the manual queue in READY_FOR_REVIEW state."""
        from ..types import utcnow

        conn = self._get_conn()
        now = utcnow()
        try:
            conn.execute(
                """INSERT INTO manual_queue
                   (brief_id, state, approval_id, image_checksum, caption_checksum,
                    bundle_path, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    brief_id,
                    ManualQueueState.READY_FOR_REVIEW,
                    approval_id,
                    image_checksum,
                    caption_checksum,
                    bundle_path,
                    now,
                    now,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise QueueError(f"Brief {brief_id} already in manual queue") from None

    def get(self, brief_id: str) -> dict | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM manual_queue WHERE brief_id = ?", (brief_id,)).fetchone()
        return dict(row) if row else None

    def transition(self, brief_id: str, new_state: str, **kwargs: str) -> dict:
        """Transition a brief to a new state. Raises on invalid transition."""
        from ..types import utcnow

        conn = self._get_conn()
        current = self.get(brief_id)
        if current is None:
            raise QueueError(f"Brief {brief_id} not in queue")

        current_state = current["state"]
        if new_state not in _VALID_MANUAL_TRANSITIONS.get(current_state, set()):
            raise QueueError(f"Cannot transition {brief_id} from {current_state} to {new_state}")

        now = utcnow()
        updates = {"state": new_state, "updated_at": now}
        updates.update(kwargs)

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = [*list(updates.values()), brief_id]
        conn.execute(f"UPDATE manual_queue SET {set_clause} WHERE brief_id = ?", values)
        conn.commit()
        return self.get(brief_id)  # type: ignore[return-value]

    def list_by_state(self, state: str, limit: int = 100) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM manual_queue WHERE state = ? ORDER BY created_at ASC LIMIT ?",
            (state, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_all(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM manual_queue ORDER BY created_at ASC").fetchall()
        return [dict(r) for r in rows]

    def count(self, state: str | None = None) -> int:
        conn = self._get_conn()
        if state:
            row = conn.execute(
                "SELECT COUNT(*) FROM manual_queue WHERE state = ?", (state,)
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM manual_queue").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
