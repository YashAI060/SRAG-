"""
Vector Store — Qdrant wrapper with full tenant isolation and chunk metadata.

Security guarantee:
    tenant_id is ALWAYS injected from the server-side authenticated user.
    It is NEVER accepted from the client request body.

Chunk payload schema (stored in Qdrant):
    {
        "chunk_id":    "uuid4",
        "document_id": "uuid4",
        "tenant_id":   "user@example.com",
        "filename":    "policy.pdf",
        "page_number": 4,
        "chunk_index": 42,
        "text":        "...",
        "version":     1,
        "is_active":   true
    }
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import settings

import threading
_local_qdrant_client = None
_qdrant_lock = threading.Lock()

class VectorStoreService:
    def __init__(self):
        global _local_qdrant_client
        if settings.QDRANT_URL.startswith("http"):
            self.client = QdrantClient(url=settings.QDRANT_URL)
        else:
            with _qdrant_lock:
                if _local_qdrant_client is None:
                    _local_qdrant_client = QdrantClient(path=settings.QDRANT_URL)
            self.client = _local_qdrant_client
        self.collection_name = settings.QDRANT_COLLECTION
        self.vector_size = settings.EMBEDDING_DIMENSIONS
        self._ensure_collection_exists()

    # ── Collection management ──────────────────────────────────────────────────

    def _ensure_collection_exists(self):
        with _qdrant_lock:
            collections = self.client.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size, distance=Distance.COSINE
                    ),
                )

    # ── Write ──────────────────────────────────────────────────────────────────

    def add_documents(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        document_id: str,
        tenant_id: str,
        filename: str,
        version: int = 1,
    ) -> int:
        """
        Upsert chunks with full metadata payload.
        Returns the number of points upserted.
        """
        points = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload={
                        "chunk_id":    chunk_id,
                        "document_id": document_id,
                        "tenant_id":   tenant_id,
                        "filename":    filename,
                        "page_number": chunk.get("page_number", 0),
                        "chunk_index": chunk.get("chunk_index", idx),
                        "text":        chunk["text"],
                        "contextualized_text": chunk.get("contextualized_text", chunk["text"]),
                        "version":     version,
                        "is_active":   True,
                    },
                )
            )
        if points:
            with _qdrant_lock:
                self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)

    def deactivate_document_chunks(self, document_id: str, tenant_id: str) -> None:
        """Mark old version chunks inactive (for document versioning)."""
        # Qdrant doesn't support in-place payload updates via filter in all client versions.
        # Best approach: delete old points and re-index. For MVP: use payload flag.
        # This is a known limitation documented in ADR-002.
        with _qdrant_lock:
            self.client.set_payload(
                collection_name=self.collection_name,
                payload={"is_active": False},
                points=Filter(
                    must=[
                        FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                        FieldCondition(key="tenant_id",   match=MatchValue(value=tenant_id)),
                    ]
                ),
            )

    def delete_document_chunks(self, document_id: str, tenant_id: str) -> None:
        """Hard delete all chunks for a document."""
        with _qdrant_lock:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                        FieldCondition(key="tenant_id",   match=MatchValue(value=tenant_id)),
                    ]
                ),
            )

    # ── Read ───────────────────────────────────────────────────────────────────

    def search_documents(
        self,
        query_embedding: list[float],
        tenant_id: str,
        limit: int = settings.RETRIEVAL_TOP_K,
        document_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Dense similarity search scoped to a single tenant.
        Optional document_ids for per-query document filtering.
        """
        must_conditions = [
            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
            FieldCondition(key="is_active", match=MatchValue(value=True)),
        ]

        if document_ids:
            # Qdrant doesn't natively support "in" — use nested should
            from qdrant_client.http.models import Filter as QFilter
            must_conditions.append(
                QFilter(
                    should=[
                        FieldCondition(key="document_id", match=MatchValue(value=did))
                        for did in document_ids
                    ]
                )
            )

        query_filter = Filter(must=must_conditions)
        with _qdrant_lock:
            try:
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding,
                    limit=limit,
                    query_filter=query_filter,
                    with_payload=True,
                )
            except Exception as e:
                logger.warning(f"Qdrant vector search failed (recovering gracefully): {e}")
                hits = []
        return [
            {
                "chunk_id":    hit.payload.get("chunk_id", str(hit.id)),
                "document_id": hit.payload.get("document_id", ""),
                "tenant_id":   hit.payload.get("tenant_id", ""),
                "filename":    hit.payload.get("filename", "Unknown"),
                "page_number": hit.payload.get("page_number", 0),
                "chunk_index": hit.payload.get("chunk_index", 0),
                "text":        hit.payload.get("text", ""),
                "score":       hit.score,
            }
            for hit in hits
        ]

    def get_all_chunks(self, tenant_id: str, batch_size: int = 1000) -> list[dict]:
        """
        Scroll through all active chunks for a tenant (used for BM25 index rebuild).
        """
        chunks = []
        offset = None
        with _qdrant_lock:
            while True:
                results, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                            FieldCondition(key="is_active", match=MatchValue(value=True)),
                        ]
                    ),
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                )
                for point in results:
                    chunks.append({
                        "chunk_id":    point.payload.get("chunk_id", str(point.id)),
                        "document_id": point.payload.get("document_id", ""),
                        "tenant_id":   point.payload.get("tenant_id", ""),
                        "filename":    point.payload.get("filename", ""),
                        "page_number": point.payload.get("page_number", 0),
                        "text":        point.payload.get("text", ""),
                    })
                if next_offset is None:
                    break
                offset = next_offset
        return chunks