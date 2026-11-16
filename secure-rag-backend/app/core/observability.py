"""
Structured observability: per-query trace logging.
Each query produces a QueryTrace written as a JSONL line for easy parsing
by analysis tools or a future Grafana/Prometheus stack.
"""
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Any

from app.core.config import settings


@dataclass
class QueryTrace:
    query_id: str = field(default_factory=lambda: f"q_{uuid.uuid4().hex[:8]}")
    tenant_id: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # ── Latency (ms) ─────────────────────────────────────────────────────────
    embedding_ms: float = 0.0
    decomposition_latency_ms: float = 0.0
    bm25_ms: float = 0.0
    dense_ms: float = 0.0
    rrf_ms: float = 0.0
    rerank_ms: float = 0.0
    confidence_ms: float = 0.0
    llm_ms: float = 0.0
    total_ms: float = 0.0

    # ── Retrieval ─────────────────────────────────────────────────────────────
    decomposition_status: str = "INACTIVE"
    subquery_count: int = 0
    subqueries_requested: int = 0
    subqueries_accepted: int = 0
    subqueries_truncated: bool = False
    retrieved_chunks: int = 0
    reranked_chunks: int = 0
    top_dense_score: float = 0.0
    top_rrf_score: float = 0.0

    # ── Confidence ────────────────────────────────────────────────────────────
    confidence: float = 0.0
    decision: str = ""   # "answer" | "abstain"

    # ── Generation ────────────────────────────────────────────────────────────
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    model: str = settings.GENERATION_MODEL

    # ── Error / Failure Taxonomy ───────────────────────────────────
    error: Optional[str] = None
    failure_reason: Optional[str] = None   # RETRIEVAL_EMPTY | LOW_CONFIDENCE | GENERATION_ERROR
    
    reranker: Optional[Any] = None
    generation: Optional[Any] = None


def log_trace(trace: QueryTrace) -> None:
    """Append a QueryTrace as a JSONL line to the trace log file."""
    if not settings.LOG_QUERY_TRACES:
        return
    try:
        with open(settings.TRACE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(trace)) + "\n")
    except Exception:
        pass  # Observability must never break the critical path


class Timer:
    """Context manager for measuring elapsed milliseconds."""

    def __init__(self):
        self.elapsed_ms: float = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
