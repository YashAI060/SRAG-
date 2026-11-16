"""Unit tests for CitationValidator."""
import pytest
from app.rag.citation_validator import CitationValidator


@pytest.fixture
def validator():
    return CitationValidator()


def _chunk(chunk_id: str, doc_id: str = "doc1", page: int = 1) -> dict:
    return {
        "chunk_id": chunk_id,
        "document_id": doc_id,
        "filename": "test.pdf",
        "page_number": page,
        "text": f"Text content for chunk {chunk_id}",
        "score": 0.85,
        "dense_score": 0.85,
        "rrf_score": 0.75,
    }


class TestCitationValidator:
    def test_valid_citations_resolved(self, validator):
        retrieved = [_chunk("c1"), _chunk("c2"), _chunk("c3")]
        cited = ["c1", "c3"]
        valid, hallucinated = validator.validate_and_resolve(cited, retrieved)
        assert len(valid) == 2
        assert len(hallucinated) == 0
        assert {c.chunk_id for c in valid} == {"c1", "c3"}

    def test_hallucinated_chunk_id_detected(self, validator):
        retrieved = [_chunk("c1"), _chunk("c2")]
        cited = ["c1", "invented_id_xyz"]
        valid, hallucinated = validator.validate_and_resolve(cited, retrieved)
        assert len(valid) == 1
        assert "invented_id_xyz" in hallucinated

    def test_empty_cited_returns_empty(self, validator):
        retrieved = [_chunk("c1")]
        valid, hallucinated = validator.validate_and_resolve([], retrieved)
        assert valid == []
        assert hallucinated == []

    def test_empty_retrieved_all_hallucinated(self, validator):
        valid, hallucinated = validator.validate_and_resolve(["c1", "c2"], [])
        assert valid == []
        assert set(hallucinated) == {"c1", "c2"}

    def test_citation_precision_all_valid(self, validator):
        cited = ["c1", "c2"]
        retrieved = [_chunk("c1"), _chunk("c2")]
        valid, hall = validator.validate_and_resolve(cited, retrieved)
        prec = validator.citation_precision(valid, hall)
        assert prec == 1.0

    def test_citation_precision_half_hallucinated(self, validator):
        cited = ["c1", "fake"]
        retrieved = [_chunk("c1")]
        valid, hall = validator.validate_and_resolve(cited, retrieved)
        prec = validator.citation_precision(valid, hall)
        assert prec == 0.5

    def test_citation_metadata_correct(self, validator):
        retrieved = [_chunk("c1", doc_id="doc_abc", page=17)]
        valid, _ = validator.validate_and_resolve(["c1"], retrieved)
        assert valid[0].page_number == 17
        assert valid[0].document_id == "doc_abc"
        assert valid[0].source_file == "test.pdf"

    def test_retrieval_score_preserved(self, validator):
        retrieved = [_chunk("c1")]
        valid, _ = validator.validate_and_resolve(["c1"], retrieved)
        assert valid[0].retrieval_score == 0.85
        assert valid[0].rrf_score == 0.75
