"""
Document Registry — SQLite-backed metadata store.

Separation of concerns:
    Qdrant  → "Which chunks are relevant?"
    SQLite  → "Which documents does this user own?"
               "Is this document currently processing?"
               "Who uploaded it and when?"

This service is architected so the SQLite backend can be swapped for
PostgreSQL by changing only this file (see ADR docs/decisions/001-sqlite-vs-postgres.md).

Features:
    - UUID document_id (not filename-based)
    - SHA-256 deduplication for idempotent ingestion
    - Document versioning (same filename → new version, old deactivated)
    - Processing status tracking (pending → processing → ready | failed)
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings


# ── Schema ────────────────────────────────────────────────────────────────────

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    document_id     TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    filename        TEXT NOT NULL,
    file_hash       TEXT NOT NULL,
    file_size       INTEGER,
    page_count      INTEGER DEFAULT 0,
    chunk_count     INTEGER DEFAULT 0,
    version         INTEGER DEFAULT 1,
    is_active       INTEGER DEFAULT 1,
    status          TEXT DEFAULT 'pending',
    error_message   TEXT,
    processing_ms   REAL,
    uploaded_by     TEXT,
    uploaded_at     TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tenant   ON documents (tenant_id);
CREATE INDEX IF NOT EXISTS idx_hash     ON documents (file_hash, tenant_id);
CREATE INDEX IF NOT EXISTS idx_active   ON documents (tenant_id, is_active);
"""


class DocumentStore:
    """Thread-safe SQLite document registry."""

    def __init__(self, db_path: str = settings.SQLITE_DB_PATH):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.db_path = db_path
        self._init_db()

    # ── Context manager ───────────────────────────────────────────────────────

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(_CREATE_TABLE)

    # ── SHA-256 deduplication ─────────────────────────────────────────────────

    @staticmethod
    def compute_hash(file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    def find_by_hash(self, file_hash: str, tenant_id: str) -> Optional[dict]:
        """
        Check if this exact file has already been ingested for this tenant.
        Returns the document record if found (idempotent upload guard).
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE file_hash=? AND tenant_id=? AND is_active=1",
                (file_hash, tenant_id),
            ).fetchone()
        return dict(row) if row else None

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(
        self,
        tenant_id: str,
        filename: str,
        file_hash: str,
        file_size: int,
        uploaded_by: str,
    ) -> tuple[str, list[str]]:
        """
        Register a new document. If same filename already exists for tenant,
        deactivate old versions and bump version number.
        Returns (new_document_id, deactivated_document_ids).
        """
        now = datetime.now(timezone.utc).isoformat()
        document_id = str(uuid.uuid4())
        deactivated_ids = []

        # Compute next version number
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT MAX(version) as v FROM documents WHERE tenant_id=? AND filename=?",
                (tenant_id, filename),
            ).fetchone()
            version = (existing["v"] or 0) + 1

            # Deactivate previous versions
            if version > 1:
                # Find the ids that are currently active
                active_rows = conn.execute(
                    "SELECT document_id FROM documents WHERE tenant_id=? AND filename=? AND is_active=1",
                    (tenant_id, filename),
                ).fetchall()
                deactivated_ids = [row["document_id"] for row in active_rows]
                
                if deactivated_ids:
                    conn.execute(
                        "UPDATE documents SET is_active=0, updated_at=? WHERE tenant_id=? AND filename=? AND is_active=1",
                        (now, tenant_id, filename),
                    )

            conn.execute(
                """INSERT INTO documents
                   (document_id, tenant_id, filename, file_hash, file_size, version,
                    is_active, status, uploaded_by, uploaded_at, updated_at)
                   VALUES (?,?,?,?,?,?,1,'pending',?,?,?)""",
                (document_id, tenant_id, filename, file_hash, file_size,
                 version, uploaded_by, now, now),
            )
        return document_id, deactivated_ids

    def update_status(
        self,
        document_id: str,
        status: str,
        chunk_count: int = 0,
        page_count: int = 0,
        processing_ms: float = 0.0,
        error_message: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """UPDATE documents
                   SET status=?, chunk_count=?, page_count=?,
                       processing_ms=?, error_message=?, updated_at=?
                   WHERE document_id=?""",
                (status, chunk_count, page_count, processing_ms, error_message, now, document_id),
            )

    def get(self, document_id: str, tenant_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE document_id=? AND tenant_id=?",
                (document_id, tenant_id),
            ).fetchone()
        return dict(row) if row else None

    def list_for_tenant(self, tenant_id: str, active_only: bool = True) -> list[dict]:
        with self._conn() as conn:
            query = "SELECT * FROM documents WHERE tenant_id=?"
            params: list = [tenant_id]
            if active_only:
                query += " AND is_active=1"
            query += " ORDER BY uploaded_at DESC"
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def delete(self, document_id: str, tenant_id: str) -> bool:
        """Soft-delete: marks is_active=0."""
        with self._conn() as conn:
            result = conn.execute(
                "UPDATE documents SET is_active=0, updated_at=? WHERE document_id=? AND tenant_id=?",
                (datetime.now(timezone.utc).isoformat(), document_id, tenant_id),
            )
        return result.rowcount > 0


# Singleton instance
document_store = DocumentStore()
