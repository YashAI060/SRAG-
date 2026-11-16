"""
Hybrid Retrieval: Dense (Gemini embeddings) + BM25 → Reciprocal Rank Fusion.

Architecture:
    Query
      ↓
    Dense search (Qdrant cosine)      BM25 search (rank-bm25)
      ↓                                   ↓
    Top-K dense hits               Top-K BM25 hits
      └──────────── RRF fusion ──────────┘
                        ↓
                 Unified ranked list

BM25 index is built in-memory at startup from the stored corpus.
On document upload, call `add_documents()` to update the index.

NOTE: For production scale, replace the in-memory BM25 index with
Qdrant's native sparse vector support (SparseVector + BM42/SPLADE).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional, Tuple

from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.services.vector_store import VectorStoreService


class HybridRetriever:
    """
    Combines dense (semantic) and BM25 (lexical) retrieval via RRF.
    """

    def __init__(self):
        self.vector_store = VectorStoreService()
        # corpus is loaded lazily / rebuilt on ingestion
        self._bm25: Optional[BM25Okapi] = None
        self._corpus_chunks: list[dict] = []   # parallel to BM25 index rows

    # ──────────────────────────────────────────────────────────────────────────
    # Index management
    # ──────────────────────────────────────────────────────────────────────────

    def rebuild_bm25_index(self, tenant_id: str) -> None:
        """
        Rebuild the in-memory BM25 index for a tenant from Qdrant payloads.
        Call after ingestion or on startup if persistence is needed.
        """
        chunks = self.vector_store.get_all_chunks(tenant_id=tenant_id)
        self._corpus_chunks = chunks
        if chunks:
            tokenised = [c["text"].lower().split() for c in chunks]
            self._bm25 = BM25Okapi(tokenised)

    # ──────────────────────────────────────────────────────────────────────────
    # Retrieval
    # ──────────────────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        query_embedding: list[float],
        tenant_id: str,
        top_k: int = settings.RETRIEVAL_TOP_K,
        document_ids: Optional[list[str]] = None,   # optional per-query doc filter
        mode: str = "full",
        decompose: bool = False,
    ) -> Tuple[list[dict], dict]:
        """
        Returns (top_k_chunks, decomp_trace)
        fused via RRF, each chunk annotated with:
            chunk_id, text, filename, page_number, document_id,
            dense_score, bm25_score, rrf_score
        """
        decomp_trace = {"status": "INACTIVE", "latency_ms": 0.0, "subquery_count": 0, "subqueries_requested": 0, "subqueries_accepted": 0, "subqueries_truncated": False}
        queries_to_run = [(query, query_embedding)]
        
        if decompose:
            from app.services.llm_generator import LLMGeneratorService
            llm_svc = LLMGeneratorService()
            subqueries, d_trace = llm_svc.decompose_query(query)
            decomp_trace.update(d_trace)
            decomp_trace["subquery_count"] = len(subqueries)
            
            for sq in subqueries:
                sq_emb = llm_svc.get_embedding(sq, task_type="retrieval_query")
                queries_to_run.append((sq, sq_emb))

        dense_branches = []
        bm25_branches = []

        for q, q_emb in queries_to_run:
            if mode in ("dense", "hybrid", "hybrid_rerank", "full"):
                dense_branches.append(self._dense_search(
                    q_emb, tenant_id, top_k, document_ids
                ))
            
            if mode in ("bm25", "hybrid", "hybrid_rerank", "full"):
                bm25_branches.append(self._bm25_search(q, tenant_id, top_k))

        if mode == "dense":
            all_dense = [hit for branch in dense_branches for hit in branch]
            fused = sorted(all_dense, key=lambda x: x.get("dense_score", 0.0), reverse=True)
            seen = set()
            deduped = []
            for c in fused:
                cid = c.get("chunk_id")
                if cid not in seen:
                    c["score"] = c.get("dense_score", 0.0)
                    deduped.append(c)
                    seen.add(cid)
            return deduped[:top_k], decomp_trace
            
        if mode == "bm25":
            all_bm25 = [hit for branch in bm25_branches for hit in branch]
            fused = sorted(all_bm25, key=lambda x: x.get("bm25_score", 0.0), reverse=True)
            seen = set()
            deduped = []
            for c in fused:
                cid = c.get("chunk_id")
                if cid not in seen:
                    c["score"] = c.get("bm25_score", 0.0)
                    deduped.append(c)
                    seen.add(cid)
            return deduped[:top_k], decomp_trace

        fused = self._rrf_fuse(dense_branches, bm25_branches, k=settings.RRF_K)
        return fused[:top_k], decomp_trace

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _dense_search(
        self,
        query_embedding: list[float],
        tenant_id: str,
        top_k: int,
        document_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        results = self.vector_store.search_documents(
            query_embedding=query_embedding,
            tenant_id=tenant_id,
            limit=top_k,
            document_ids=document_ids,
        )
        for r in results:
            r["dense_score"] = r.pop("score", 0.0)
        return results

    def _bm25_search(
        self, query: str, tenant_id: str, top_k: int
    ) -> list[dict]:
        if self._bm25 is None or not self._corpus_chunks:
            # Index not built yet — rebuild now (first query)
            self.rebuild_bm25_index(tenant_id)

        if self._bm25 is None:
            return []

        tokenised_query = query.lower().split()
        scores = self._bm25.get_scores(tokenised_query)

        # Pair scores with chunks, keep tenant's chunks only
        ranked = sorted(
            [
                (score, chunk)
                for score, chunk in zip(scores, self._corpus_chunks)
                if chunk.get("tenant_id") == tenant_id
            ],
            key=lambda x: x[0],
            reverse=True,
        )[:top_k]

        results = []
        for score, chunk in ranked:
            results.append({**chunk, "bm25_score": float(score)})
        return results

    @staticmethod
    def _rrf_fuse(
        dense_hits_lists: list[list[dict]],
        bm25_hits_lists: list[list[dict]],
        k: int = 60,
    ) -> list[dict]:
        """
        Reciprocal Rank Fusion (Multi-query):
            score(d) = sum(1 / (k + rank_i(d))) across all branches
        """
        chunk_scores: dict[str, float] = defaultdict(float)
        chunk_data: dict[str, dict] = {}

        # Defensive normalization if a single flat list was passed
        if dense_hits_lists and isinstance(dense_hits_lists[0], dict):
            dense_hits_lists = [dense_hits_lists]
        if bm25_hits_lists and isinstance(bm25_hits_lists[0], dict):
            bm25_hits_lists = [bm25_hits_lists]

        for dense_hits in dense_hits_lists:
            for rank, hit in enumerate(dense_hits):
                cid = hit.get("chunk_id", hit.get("text", "")[:32])
                chunk_scores[cid] += 1.0 / (k + rank + 1)
                chunk_data[cid] = hit

        for bm25_hits in bm25_hits_lists:
            for rank, hit in enumerate(bm25_hits):
                cid = hit.get("chunk_id", hit.get("text", "")[:32])
                chunk_scores[cid] += 1.0 / (k + rank + 1)
                if cid not in chunk_data:
                    chunk_data[cid] = hit
                else:
                    chunk_data[cid]["bm25_score"] = hit.get("bm25_score", 0.0)

        sorted_ids = sorted(chunk_scores, key=lambda cid: chunk_scores[cid], reverse=True)
        fused = []
        for cid in sorted_ids:
            entry = chunk_data[cid].copy()
            entry["rrf_score"] = round(chunk_scores[cid], 6)
            # Use RRF score as the primary `.score` field for downstream consumers
            entry["score"] = entry["rrf_score"]
            fused.append(entry)
        return fused
