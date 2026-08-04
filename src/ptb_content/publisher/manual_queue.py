"""Manual publish queue for semi-automated Instagram scheduling.

States:
    READY_FOR_REVIEW → APPROVED → READY_FOR_MANUAL_SCHEDULING →
    MANUALLY_SCHEDULED → PUBLISHED_CONFIRMED | CANCELLED
"""

from __future__ import annotations

import json
import os
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


def _resolve_db_path(user_override: Path | str | None = None) -> Path:
    if user_override is not None:
        return Path(user_override)
    env_path = os.environ.get("PTB_MANUAL_QUEUE_DB")
    if env_path:
        return Path(env_path)
    return project_root() / "data" / "manual-queue.db"


class ManualQueue:
    """SQLite-backed queue whose identity is derived from the exported manifest."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = _resolve_db_path(db_path)
        ensure_dir(self.db_path.parent)
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            try:
                self._conn = sqlite3.connect(str(self.db_path))
            except sqlite3.OperationalError as exc:
                raise QueueError(
                    f"Cannot open database at {self.db_path}: {exc}. "
                    "Check that the directory exists and has write permissions."
                ) from None
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

    def health_check(self) -> dict[str, str | bool]:
        try:
            conn = self._get_conn()
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _health_check (id INTEGER PRIMARY KEY, ts TEXT)"
            )
            conn.execute("INSERT INTO _health_check (ts) VALUES (datetime('now'))")
            conn.commit()
            row = conn.execute("SELECT COUNT(*) FROM _health_check").fetchone()
            count = row[0] if row else 0
            conn.execute("DROP TABLE IF EXISTS _health_check")
            conn.commit()
            return {
                "status": "healthy",
                "db_path": str(self.db_path),
                "writable": True,
                "readable": True,
                "test_rows": count,
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "db_path": str(self.db_path),
                "error": str(exc),
                "writable": False,
                "readable": False,
            }

    @staticmethod
    def _validated_manifest(brief_id: str, bundle_path: str) -> dict:
        if not bundle_path:
            raise QueueError("bundle_path is required")
        bundle = Path(bundle_path)
        manifest_path = bundle / "manifest.json"
        checksums_path = bundle / "checksums.sha256"
        if not manifest_path.exists() or not checksums_path.exists():
            raise QueueError("Bundle is missing manifest.json or checksums.sha256")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise QueueError(f"Cannot read bundle manifest: {exc}") from None
        if manifest.get("brief_id") != brief_id:
            raise QueueError("Bundle manifest brief_id mismatch")
        manifest_approval = str(manifest.get("approval_id", "")).strip()
        if not manifest_approval:
            raise QueueError("Bundle manifest has empty approval_id")
        if manifest.get("publish_status") != "READY_FOR_MANUAL_SCHEDULING":
            raise QueueError("Bundle is not marked READY_FOR_MANUAL_SCHEDULING")
        if manifest.get("publication_risk_level") != "LOW":
            raise QueueError("Only LOW publication-risk bundles may enter manual scheduling")
        return manifest

    def add(
        self,
        brief_id: str,
        approval_id: str = "",
        image_checksum: str = "",
        caption_checksum: str = "",
        bundle_path: str = "",
    ) -> None:
        """Add a manifest-validated bundle in READY_FOR_REVIEW state."""
        from ..types import utcnow

        manifest = self._validated_manifest(brief_id, bundle_path)
        manifest_approval = str(manifest["approval_id"])
        if approval_id and approval_id != manifest_approval:
            raise QueueError("Queue approval_id does not match bundle manifest")
        approval_id = manifest_approval
        caption_checksum = str(manifest.get("caption_checksum", caption_checksum))
        image_checksum = str(manifest.get("brief_checksum", image_checksum))

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
        set_clause = ", ".join(f"{key} = ?" for key in updates)
        values = [*updates.values(), brief_id]
        conn.execute(f"UPDATE manual_queue SET {set_clause} WHERE brief_id = ?", values)
        conn.commit()
        return self.get(brief_id)  # type: ignore[return-value]

    def list_by_state(self, state: str, limit: int = 100) -> list[dict]:
        rows = self._get_conn().execute(
            "SELECT * FROM manual_queue WHERE state = ? ORDER BY created_at ASC LIMIT ?",
            (state, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_all(self) -> list[dict]:
        rows = self._get_conn().execute(
            "SELECT * FROM manual_queue ORDER BY created_at ASC"
        ).fetchall()
        return [dict(row) for row in rows]

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
