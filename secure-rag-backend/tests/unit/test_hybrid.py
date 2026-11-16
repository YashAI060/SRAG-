"""Unit tests for HybridRetriever RRF fusion logic."""
import pytest
from app.rag.hybrid_retrieval import HybridRetriever


class TestRRFFusion:
    def _hit(self, chunk_id: str, score: float, bm25: float = 0.0) -> dict:
        return {
            "chunk_id": chunk_id,
            "text": f"text for {chunk_id}",
            "score": score,
            "dense_score": score,
            "bm25_score": bm25,
            "filename": "test.pdf",
            "page_number": 1,
        }

    def test_rrf_returns_merged_results(self):
        dense = [self._hit("c1", 0.9), self._hit("c2", 0.8)]
        bm25  = [self._hit("c3", 0.0, 5.0), self._hit("c1", 0.0, 4.5)]
        fused = HybridRetriever._rrf_fuse([dense], [bm25], k=60)
        ids = [r["chunk_id"] for r in fused]
        # c1 appears in both lists → should rank highest
        assert ids[0] == "c1"
        assert set(ids) == {"c1", "c2", "c3"}

    def test_rrf_score_annotation(self):
        dense = [self._hit("a", 0.9)]
        bm25  = [self._hit("a", 0.0, 3.0)]
        fused = HybridRetriever._rrf_fuse([dense], [bm25], k=60)
        assert "rrf_score" in fused[0]
        assert fused[0]["rrf_score"] > 0.0

    def test_rrf_empty_lists(self):
        fused = HybridRetriever._rrf_fuse([], [], k=60)
        assert fused == []

    def test_rrf_dense_only(self):
        dense = [self._hit("x", 0.95), self._hit("y", 0.80)]
        fused = HybridRetriever._rrf_fuse([dense], [[]], k=60)
        assert [r["chunk_id"] for r in fused] == ["x", "y"]

    def test_rrf_order_preserved(self):
        dense = [self._hit(f"c{i}", 0.9 - i * 0.1) for i in range(5)]
        fused = HybridRetriever._rrf_fuse([dense], [[]], k=60)
        # With no BM25 contribution, dense rank order is preserved
        assert [r["chunk_id"] for r in fused] == [f"c{i}" for i in range(5)]

    def test_rrf_cross_list_boost(self):
        """A chunk in both lists should outscore a chunk appearing only in dense."""
        dense = [self._hit("shared", 0.70), self._hit("dense_only", 0.95)]
        bm25  = [self._hit("shared", 0.0, 10.0)]
        fused = HybridRetriever._rrf_fuse([dense], [bm25], k=60)
        # 'shared' appears in both → should beat 'dense_only' despite lower dense score
        ids = [r["chunk_id"] for r in fused]
        assert ids[0] == "shared"
