"""SQLite-based publish queue with idempotency and WAL mode."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..utils.helpers import ensure_dir, project_root
from .errors import IdempotencyViolationError, QueueError
from .protocol import PublishJob, PublishState


class PublishQueue:
    """Thread-safe publish queue backed by SQLite WAL.

    Enforces idempotency: duplicate (brief_id, content_checksum, account_id) blocked.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = project_root() / "data" / "publish-queue.db"
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
            CREATE TABLE IF NOT EXISTS publish_jobs (
                job_id TEXT PRIMARY KEY,
                brief_id TEXT NOT NULL,
                content_checksum TEXT NOT NULL,
                instagram_account_id TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'DRAFT',
                media_id TEXT,
                container_id TEXT,
                instagram_media_id TEXT,
                idempotency_key TEXT NOT NULL UNIQUE,
                error_message TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT,
                metadata TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_brief_id ON publish_jobs(brief_id);
            CREATE INDEX IF NOT EXISTS idx_state ON publish_jobs(state);
            CREATE INDEX IF NOT EXISTS idx_idempotency ON publish_jobs(idempotency_key);
        """)
        conn.commit()

    def enqueue(self, job: PublishJob) -> PublishJob:
        """Add a job to the queue. Raises IdempotencyViolationError on duplicate."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO publish_jobs
                   (job_id, brief_id, content_checksum, instagram_account_id, state,
                    media_id, container_id, instagram_media_id, idempotency_key,
                    error_message, retry_count, max_retries, created_at, updated_at,
                    published_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job.job_id,
                    job.brief_id,
                    job.content_checksum,
                    job.instagram_account_id,
                    job.state.value,
                    job.media_id,
                    job.container_id,
                    job.instagram_media_id,
                    job.idempotency_key,
                    job.error_message,
                    job.retry_count,
                    job.max_retries,
                    job.created_at,
                    job.updated_at,
                    job.published_at,
                    json.dumps(job.metadata),
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as e:
            if "idempotency_key" in str(e):
                raise IdempotencyViolationError(
                    f"Duplicate publish: {job.idempotency_key}"
                ) from e
            raise QueueError(f"Failed to enqueue job: {e}") from e
        return job

    def get(self, job_id: str) -> PublishJob | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM publish_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def get_by_idempotency_key(self, key: str) -> PublishJob | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM publish_jobs WHERE idempotency_key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def update_state(self, job_id: str, new_state: PublishState, error_message: str | None = None) -> PublishJob:
        conn = self._get_conn()

        job = self.get(job_id)
        if job is None:
            raise QueueError(f"Job not found: {job_id}")

        job.transition(new_state, error_message=error_message)

        conn.execute(
            "UPDATE publish_jobs SET state = ?, error_message = ?, updated_at = ?, published_at = ? WHERE job_id = ?",
            (job.state.value, job.error_message, job.updated_at, job.published_at, job_id),
        )
        conn.commit()
        return job

    def update_container(self, job_id: str, container_id: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE publish_jobs SET container_id = ? WHERE job_id = ?",
            (container_id, job_id),
        )
        conn.commit()

    def update_media_id(self, job_id: str, media_id: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE publish_jobs SET instagram_media_id = ? WHERE job_id = ?",
            (media_id, job_id),
        )
        conn.commit()

    def list_by_state(self, state: PublishState, limit: int = 100) -> list[PublishJob]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM publish_jobs WHERE state = ? ORDER BY created_at ASC LIMIT ?",
            (state.value, limit),
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def count_recent_posts(self, hours: int = 24) -> int:
        conn = self._get_conn()
        row = conn.execute(
            """SELECT COUNT(*) FROM publish_jobs
               WHERE state = 'PUBLISHED'
               AND published_at > datetime('now', ?)""",
            (f"-{hours} hours",),
        ).fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _row_to_job(self, row: sqlite3.Row) -> PublishJob:
        return PublishJob(
            job_id=row["job_id"],
            brief_id=row["brief_id"],
            content_checksum=row["content_checksum"],
            instagram_account_id=row["instagram_account_id"],
            state=PublishState(row["state"]),
            media_id=row["media_id"],
            container_id=row["container_id"],
            instagram_media_id=row["instagram_media_id"],
            idempotency_key=row["idempotency_key"],
            error_message=row["error_message"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            published_at=row["published_at"],
            metadata=json.loads(row["metadata"]),
        )
