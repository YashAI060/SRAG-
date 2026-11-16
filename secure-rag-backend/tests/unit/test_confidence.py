"""Unit tests for ConfidenceGate."""
import pytest
from app.rag.confidence import ConfidenceGate


@pytest.fixture
def gate():
    return ConfidenceGate(threshold=0.45)


def _make_chunks(scores: list[float]) -> list[dict]:
    return [
        {"score": s, "rrf_score": s * 0.8, "text": f"chunk {i}"}
        for i, s in enumerate(scores)
    ]


class TestConfidenceGate:
    def test_empty_chunks_returns_abstain(self, gate):
        result = gate.evaluate(chunks=[])
        assert result["decision"] == "abstain"
        assert result["confidence"] == 0.0

    def test_high_score_returns_answer(self, gate):
        chunks = _make_chunks([0.90, 0.85, 0.80])
        result = gate.evaluate(chunks=chunks)
        assert result["decision"] == "answer"
        assert result["confidence"] > 0.45

    def test_low_score_returns_abstain(self, gate):
        chunks = _make_chunks([0.10, 0.08, 0.05])
        result = gate.evaluate(chunks=chunks)
        assert result["decision"] == "abstain"
        assert result["confidence"] < 0.45

    def test_signals_are_present(self, gate):
        chunks = _make_chunks([0.70])
        result = gate.evaluate(chunks=chunks)
        assert "reranker_score" in result["signals"]
        assert "rrf_score"      in result["signals"]
        assert "context_density" in result["signals"]
        assert "threshold_used" in result["signals"]

    def test_confidence_is_clamped_between_0_and_1(self, gate):
        # Even with extreme scores, output must be in [0, 1]
        chunks = _make_chunks([2.0, 1.5])  # out-of-range scores
        result = gate.evaluate(chunks=chunks)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_custom_threshold_respected(self):
        gate_strict = ConfidenceGate(threshold=0.99)
        chunks = _make_chunks([0.80, 0.75])
        result = gate_strict.evaluate(chunks=chunks)
        assert result["decision"] == "abstain"  # high threshold → abstain

    def test_context_density_signal(self, gate):
        """More supporting chunks → higher confidence."""
        few_chunks = _make_chunks([0.55])
        many_chunks = _make_chunks([0.55, 0.52, 0.50])
        r_few  = gate.evaluate(chunks=few_chunks)
        r_many = gate.evaluate(chunks=many_chunks)
        # More supporting chunks should yield higher or equal confidence
        assert r_many["confidence"] >= r_few["confidence"]
