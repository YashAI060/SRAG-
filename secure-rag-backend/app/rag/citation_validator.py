"""
Citation Validator — backend-owned citation resolution.

Design principle:
  Gemini returns ONLY chunk_ids it used as evidence.
  This module verifies those IDs against the actual retrieved set
  and resolves them to verified metadata (filename, page, document_id).

  The LLM never invents source filenames or page numbers.
  If a cited chunk_id was not in the retrieved set → reject it.
"""
from __future__ import annotations

from typing import Optional
from app.models.schemas import Citation


class CitationValidator:
    """
    Validates and resolves chunk_ids returned by the LLM against
    the set of chunks that were actually retrieved in this query.
    """

    def validate_and_resolve(
        self,
        cited_chunk_ids: list[str],
        retrieved_chunks: list[dict],
    ) -> tuple[list[Citation], list[str]]:
        """
        Parameters
        ----------
        cited_chunk_ids : list[str]
            chunk_ids that Gemini reported using.
        retrieved_chunks : list[dict]
            Chunks that were fetched from Qdrant for this query.

        Returns
        -------
        valid_citations : list[Citation]
            Only citations whose chunk_ids appear in retrieved_chunks.
        hallucinated_ids : list[str]
            chunk_ids that Gemini cited but were NOT in retrieved_chunks.
            A non-empty list is a grounding failure.
        """
        retrieved_index: dict[str, dict] = {
            c["chunk_id"]: c for c in retrieved_chunks if "chunk_id" in c
        }

        valid_citations: list[Citation] = []
        hallucinated_ids: list[str] = []

        for cid in cited_chunk_ids:
            if cid in retrieved_index:
                chunk = retrieved_index[cid]
                valid_citations.append(
                    Citation(
                        chunk_id=cid,
                        document_id=chunk.get("document_id", ""),
                        source_file=chunk.get("filename", "Unknown"),
                        page_number=chunk.get("page_number", 0),
                        chunk_preview=chunk.get("text", "")[:200],
                        retrieval_score=round(chunk.get("dense_score", chunk.get("score", 0.0)), 4),
                        rrf_score=round(chunk.get("rrf_score", 0.0), 4),
                    )
                )
            else:
                hallucinated_ids.append(cid)

        return valid_citations, hallucinated_ids

    @staticmethod
    def citation_precision(
        valid_citations: list[Citation],
        hallucinated_ids: list[str],
    ) -> float:
        """Fraction of cited sources that were actually in the retrieved set."""
        total = len(valid_citations) + len(hallucinated_ids)
        if total == 0:
            return 1.0
        return round(len(valid_citations) / total, 4)
