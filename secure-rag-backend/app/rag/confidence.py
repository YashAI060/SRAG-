"""
Confidence Gate — calibrated multi-signal scoring.

Design principle:
  DO NOT use a single arbitrary threshold (e.g., 0.50).
  Combine multiple normalised signals via a weighted heuristic,
  then choose the abstention threshold empirically using the
  evaluation dataset (see evaluation/evaluate.py --calibrate).

Signals:
  1. top_reranker_score  — cross-encoder / reranker score for best chunk
  2. rrf_score           — Reciprocal Rank Fusion score of best chunk
  3. context_density     — fraction of top-K chunks with score > a soft floor
  4. query_alignment     — cosine similarity between query embedding and
                           the mean of top-K chunk embeddings (optional)

Weights are read from settings so they can be tuned without code changes.
"""
from __future__ import annotations

from typing import Optional
from app.core.config import settings


class ConfidenceGate:
    """
    Produces a calibrated [0, 1] confidence score from retrieval signals
    and decides whether to answer or abstain.
    """

    # Soft floor for "supporting chunk" count heuristic
    DENSITY_FLOOR = 0.30

    def __init__(self, threshold: Optional[float] = None):
        """
        threshold: override CONFIDENCE_THRESHOLD from settings.
        Leave None to use the default (which should itself be calibrated
        via evaluation, NOT guessed).
        """
        self.threshold = threshold if threshold is not None else settings.CONFIDENCE_THRESHOLD
        self.w_reranker = settings.CONFIDENCE_WEIGHT_RERANKER
        self.w_rrf = settings.CONFIDENCE_WEIGHT_RRF
        self.w_density = settings.CONFIDENCE_WEIGHT_DENSITY
        self.w_alignment = settings.CONFIDENCE_WEIGHT_ALIGNMENT

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def evaluate(
        self,
        chunks: list[dict],
        query_embedding: Optional[list[float]] = None,
    ) -> dict:
        """
        Parameters
        ----------
        chunks : list[dict]
            Each dict has at minimum: ``score`` (reranker/cosine),
            ``rrf_score`` (float), ``text`` (str).
        query_embedding : list[float], optional
            If provided, used to compute query alignment signal.

        Returns
        -------
        dict with keys:
            ``confidence`` (float 0–1),
            ``decision``   ("answer" | "abstain"),
            ``signals``    (breakdown dict for tracing/debugging)
        """
        if not chunks:
            return self._abstain(signals={"reason": "no_chunks"})

        top = chunks[0]

        # ── Signal 1: reranker/dense score ────────────────────────────────────
        # Preference order:
        #   1. reranker_score — explicit LLM reranker judgment (0–1)
        #   2. dense_score    — cosine similarity from the embedding model (0–1)
        #   3. score          — fallback (may be RRF score if hybrid, which is tiny)
        # We avoid using raw rrf_score here because RRF by design produces very
        # small values (~1/(k+rank)) that are NOT in [0,1] after normalisation.
        raw_reranker = (
            top.get("reranker_score")
            or top.get("dense_score")
            or top.get("score", 0.0)
        )
        s_reranker = self._clamp(raw_reranker)

        # ── Signal 2: RRF score — normalised to its theoretical max ──────────
        # RRF max for rank-0 = 1 / (k + 1). With default k=60, max ≈ 0.0163.
        # We scale by (k + 1) so rank-0 → 1.0 and the signal is comparable.
        rrf_k = settings.RRF_K
        raw_rrf = top.get("rrf_score", 0.0)
        s_rrf = self._clamp(raw_rrf * (rrf_k + 1))

        # ── Signal 3: context density ─────────────────────────────────────────
        # Use dense_score for the density threshold since score=rrf_score is tiny.
        DENSE_FLOOR = 0.40
        supporting = sum(
            1 for c in chunks
            if (c.get("dense_score") or c.get("score", 0.0)) > DENSE_FLOOR
        )
        s_density = min(supporting, settings.RERANK_TOP_K) / max(settings.RERANK_TOP_K, 1)

        # ── Signal 4: query–context alignment (optional) ─────────────────────
        s_alignment = 0.5  # neutral default when not computed
        if query_embedding and len(chunks) > 0:
            s_alignment = self._mean_cosine(query_embedding, chunks)

        # ── Weighted sum ──────────────────────────────────────────────────────
        if s_rrf == 0.0:
            # In single-retriever mode (DENSE or BM25), re-normalize over active weights
            active_weights = self.w_reranker + self.w_density + self.w_alignment
            confidence = (
                self.w_reranker * s_reranker
                + self.w_density * s_density
                + self.w_alignment * s_alignment
            ) / max(active_weights, 0.01)
        else:
            confidence = (
                self.w_reranker * s_reranker
                + self.w_rrf     * s_rrf
                + self.w_density * s_density
                + self.w_alignment * s_alignment
            )
        confidence = round(self._clamp(confidence), 4)

        signals = {
            "reranker_score": round(s_reranker, 4),
            "rrf_score": round(s_rrf, 4),
            "context_density": round(s_density, 4),
            "query_alignment": round(s_alignment, 4),
            "weights": {
                "reranker": self.w_reranker,
                "rrf": self.w_rrf,
                "density": self.w_density,
                "alignment": self.w_alignment,
            },
            "threshold_used": self.threshold,
        }

        if confidence >= self.threshold:
            return {"confidence": confidence, "decision": "answer", "signals": signals}
        return {"confidence": confidence, "decision": "abstain", "signals": signals}

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, v))

    @staticmethod
    def _mean_cosine(query_emb: list[float], chunks: list[dict]) -> float:
        """
        Compute mean cosine similarity between query and top chunk embeddings.
        Falls back to 0.5 if chunk embeddings are not stored.
        """
        import math

        chunk_embs = [c.get("embedding") for c in chunks if c.get("embedding")]
        if not chunk_embs:
            return 0.5

        def dot(a, b):
            return sum(x * y for x, y in zip(a, b))

        def norm(v):
            return math.sqrt(sum(x * x for x in v)) or 1e-9

        similarities = [
            dot(query_emb, emb) / (norm(query_emb) * norm(emb))
            for emb in chunk_embs
        ]
        raw = sum(similarities) / len(similarities)
        # cosine ∈ [-1, 1] → normalise to [0, 1]
        return (raw + 1.0) / 2.0

    @staticmethod
    def _abstain(signals: dict) -> dict:
        return {"confidence": 0.0, "decision": "abstain", "signals": signals}
