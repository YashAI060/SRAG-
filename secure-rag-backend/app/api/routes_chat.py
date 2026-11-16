"""
Chat route — full hybrid RAG pipeline with observability.

Pipeline per request:
    1. Query rewriting (if history provided)
    2. Embed rewritten query
    3. Hybrid retrieval: BM25 + Dense → RRF  [tenant-scoped]
    4. Confidence gate (multi-signal, calibrated threshold)
    5. If abstain → return "insufficient information" response
    6. LLM generation (structured JSON output: answer + chunk_ids)
    7. Citation validation (backend resolves chunk_ids → metadata)
    8. Observability trace logged to JSONL

Failure taxonomy:
    RETRIEVAL_EMPTY    — Qdrant returned 0 chunks for the tenant
    RETRIEVAL_ERROR    — Exception during retrieval
    RERANKING_ERROR    — Exception during LLM reranking (falls back to RRF order)
    LOW_CONFIDENCE     — Retrieval succeeded but confidence below threshold
    GENERATION_ERROR   — Exception during LLM answer generation
"""
import logging
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

from app.api.dependencies import RoleChecker
from app.core.config import settings
from app.core.observability import QueryTrace, Timer, log_trace
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    ConfidenceResult,
    RAGTrace,
)
from app.rag.citation_validator import CitationValidator
from app.rag.confidence import ConfidenceGate
from app.rag.hybrid_retrieval import HybridRetriever
from app.rag.query_rewriter import rewrite_query
from app.services.llm_generator import LLMGeneratorService

router = APIRouter(prefix="/chat", tags=["Chat & Retrieval"])

_confidence_gate = ConfidenceGate()
_citation_validator = CitationValidator()


@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    current_user: dict = Depends(RoleChecker(["admin", "user"])),
):
    """
    Full hybrid RAG query endpoint.
    tenant_id is extracted from the verified JWT — never from the request body.
    """
    trace = QueryTrace(
        query_id=f"q_{uuid.uuid4().hex[:8]}",
        tenant_id=current_user["tenant_id"],
    )
    overall_start = time.perf_counter()

    try:
        tenant_id: str = current_user["tenant_id"]  # server-owned
        top_k = request.top_k or settings.RETRIEVAL_TOP_K

        # ── Step 1: Query Rewriting ───────────────────────────────────────────
        rewritten_query = query = request.query
        if request.history:
            rewritten_query = rewrite_query(request.query, request.history)

        # ── Step 2: Embed query ───────────────────────────────────────────────
        llm_svc = LLMGeneratorService()
        with Timer() as t_embed:
            query_embedding = llm_svc.get_embedding(
                rewritten_query, task_type="retrieval_query"
            )
        trace.embedding_ms = t_embed.elapsed_ms

        # ── Step 3: Hybrid Retrieval ──────────────────────────────────────────
        retriever = HybridRetriever()
        from app.rag.reranker import LLMReranker
        reranker = LLMReranker()

        # 1. Retrieve Candidate Chunks (Hybrid Search)
        with Timer() as t_retrieve:
            chunks, decomp_trace = retriever.retrieve(
                query=rewritten_query,
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                top_k=settings.RETRIEVAL_TOP_K,
                document_ids=request.document_ids,
                mode=request.retrieval_mode,
                decompose=request.decompose,
            )
        trace.retrieved_chunks = len(chunks)
        trace.decomposition_status = decomp_trace["status"]
        trace.decomposition_latency_ms = decomp_trace["latency_ms"]
        trace.subquery_count = decomp_trace["subquery_count"]
        trace.subqueries_requested = decomp_trace.get("subqueries_requested", 0)
        trace.subqueries_accepted = decomp_trace.get("subqueries_accepted", 0)
        trace.subqueries_truncated = decomp_trace.get("subqueries_truncated", False)

        if not chunks:
            # Distinguish RETRIEVAL_EMPTY from low-confidence
            trace.failure_reason = "RETRIEVAL_EMPTY"
            trace.total_ms = (time.perf_counter() - overall_start) * 1000
            log_trace(trace)
            return ChatResponse(
                query=query,
                rewritten_query=rewritten_query if rewritten_query != query else None,
                answer=(
                    "I was unable to find any relevant documents for this query. "
                    "Please ensure documents have been uploaded and try again."
                ),
                abstained=True,
                confidence=ConfidenceResult(score=0.0, decision="abstain",
                                            signals={"reason": "RETRIEVAL_EMPTY"}),
                citations=[],
                hallucinated_citation_ids=[],
                citation_precision=1.0,
                trace=_build_rag_trace(trace),
            )

        # 2. Rerank (if mode specifies it)
        with Timer() as t_rerank:
            if request.retrieval_mode in ("hybrid_rerank", "full"):
                rerank_top, rerank_trace = reranker.rerank(
                    query=rewritten_query,
                    chunks=chunks,
                    top_k=settings.RERANK_TOP_K
                )
            else:
                rerank_top = chunks[:settings.RERANK_TOP_K]
                rerank_trace = None
        trace.rerank_ms = t_rerank.elapsed_ms
        trace.reranker = rerank_trace
        trace.top_dense_score = chunks[0].get("dense_score", 0.0) if chunks else 0.0
        trace.top_rrf_score = chunks[0].get("rrf_score", 0.0) if chunks else 0.0
        # Split timing approx (full retrieve = bm25 + dense + rrf)
        trace.bm25_ms = t_retrieve.elapsed_ms * 0.35
        trace.dense_ms = t_retrieve.elapsed_ms * 0.45
        trace.rrf_ms   = t_retrieve.elapsed_ms * 0.20

        # ── Step 4: Confidence Gate ───────────────────────────────────────────
        with Timer() as t_conf:
            gate_result = _confidence_gate.evaluate(
                chunks=rerank_top,
                query_embedding=query_embedding,
            )
        trace.confidence_ms = t_conf.elapsed_ms
        trace.confidence = gate_result["confidence"]
        trace.decision = gate_result["decision"]

        confidence_result = ConfidenceResult(
            score=gate_result["confidence"],
            decision=gate_result["decision"],
            signals=gate_result["signals"],
        )

        # ── Step 5: Abstain if confidence too low ─────────────────────────────
        if gate_result["decision"] == "abstain":
            trace.failure_reason = "LOW_CONFIDENCE"
            trace.total_ms = (time.perf_counter() - overall_start) * 1000
            log_trace(trace)
            return ChatResponse(
                query=query,
                rewritten_query=rewritten_query if rewritten_query != query else None,
                answer=(
                    "I was unable to find sufficient evidence in the available documents "
                    "to answer this question confidently. Please try rephrasing or upload "
                    "additional relevant documents."
                ),
                abstained=True,
                confidence=confidence_result,
                citations=[],
                hallucinated_citation_ids=[],
                citation_precision=1.0,
                trace=_build_rag_trace(trace),
            )

        # ── Step 6: LLM Generation (structured output) ───────────────────────
        with Timer() as t_llm:
            generation_result, generation_trace = llm_svc.generate_answer(
                query=rewritten_query,
                context_chunks=rerank_top,
            )
        trace.llm_ms = t_llm.elapsed_ms
        trace.generation = generation_trace

        answer = generation_result["answer"]
        used_chunk_ids: list[str] = generation_result.get("used_chunk_ids", [])

        # ── Step 7: Citation Validation ───────────────────────────────────────
        valid_citations, hallucinated_ids = _citation_validator.validate_and_resolve(
            cited_chunk_ids=used_chunk_ids,
            retrieved_chunks=rerank_top,
        )
        citation_precision = _citation_validator.citation_precision(
            valid_citations, hallucinated_ids
        )

        # ── Step 8: Record trace ──────────────────────────────────────────────
        trace.total_ms = (time.perf_counter() - overall_start) * 1000
        log_trace(trace)

        return ChatResponse(
            query=query,
            rewritten_query=rewritten_query if rewritten_query != query else None,
            answer=answer,
            abstained=False,
            confidence=confidence_result,
            citations=valid_citations,
            hallucinated_citation_ids=hallucinated_ids,
            citation_precision=citation_precision,
            trace=_build_rag_trace(trace),
        )

    except HTTPException:
        raise  # Re-raise structured HTTP exceptions as-is
    except Exception as e:
        logger.error(
            "Query pipeline error [query_id=%s tenant=%s]: %s",
            trace.query_id, current_user.get("tenant_id", "unknown"), e,
            exc_info=True,
        )
        trace.error = type(e).__name__
        trace.failure_reason = "GENERATION_ERROR"
        trace.total_ms = (time.perf_counter() - overall_start) * 1000
        log_trace(trace)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "An internal error occurred while processing your query.",
                "request_id": trace.query_id,
            },
        )


def _build_rag_trace(trace: QueryTrace) -> RAGTrace:
    return RAGTrace(
        query_id=trace.query_id,
        decomposition_status=trace.decomposition_status,
        decomposition_latency_ms=round(trace.decomposition_latency_ms, 2),
        subquery_count=trace.subquery_count,
        subqueries_requested=trace.subqueries_requested,
        subqueries_accepted=trace.subqueries_accepted,
        subqueries_truncated=trace.subqueries_truncated,
        embedding_ms=round(trace.embedding_ms, 2),
        bm25_ms=round(trace.bm25_ms, 2),
        dense_ms=round(trace.dense_ms, 2),
        rrf_ms=round(trace.rrf_ms, 2),
        confidence_ms=round(trace.confidence_ms, 2),
        llm_ms=round(trace.llm_ms, 2),
        total_ms=round(trace.total_ms, 2),
        retrieved_chunks=trace.retrieved_chunks,
        top_dense_score=round(trace.top_dense_score, 4),
        top_rrf_score=round(trace.top_rrf_score, 4),
        reranker=trace.reranker,
        generation=trace.generation,
    )