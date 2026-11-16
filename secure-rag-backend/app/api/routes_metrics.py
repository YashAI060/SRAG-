"""
Metrics endpoint — aggregate observability from JSONL trace log.

GET /api/v1/metrics
Returns system-wide performance summary: latency percentiles,
abstention rate, avg confidence, query counts.
"""
import json
import os
from statistics import mean, median, quantiles

from fastapi import APIRouter, Depends

from app.api.dependencies import RoleChecker
from app.core.config import settings
from app.models.schemas import MetricsSummary

router = APIRouter(prefix="/metrics", tags=["Observability"])


@router.get("/", response_model=MetricsSummary)
async def get_metrics(
    current_user: dict = Depends(RoleChecker(["admin"])),
):
    """
    Aggregate metrics from the query trace log.
    Admin-only endpoint.
    """
    if not os.path.exists(settings.TRACE_LOG_PATH):
        return MetricsSummary(
            total_queries=0,
            avg_total_ms=0.0,
            avg_retrieval_ms=0.0,
            avg_llm_ms=0.0,
            abstention_rate=0.0,
            avg_confidence=0.0,
            p50_ms=0.0,
            p95_ms=0.0,
        )

    traces = []
    with open(settings.TRACE_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    traces.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not traces:
        return MetricsSummary(
            total_queries=0,
            avg_total_ms=0.0,
            avg_retrieval_ms=0.0,
            avg_llm_ms=0.0,
            abstention_rate=0.0,
            avg_confidence=0.0,
            p50_ms=0.0,
            p95_ms=0.0,
        )

    total_ms_list = [t.get("total_ms", 0) for t in traces]
    retrieval_ms_list = [
        t.get("bm25_ms", 0) + t.get("dense_ms", 0) + t.get("rrf_ms", 0)
        for t in traces
    ]
    llm_ms_list = [t.get("llm_ms", 0) for t in traces]
    confidence_list = [t.get("confidence", 0) for t in traces]
    abstentions = sum(1 for t in traces if t.get("decision") == "abstain")

    # Percentiles
    sorted_ms = sorted(total_ms_list)
    p50 = median(sorted_ms) if sorted_ms else 0.0
    p95 = quantiles(sorted_ms, n=20)[18] if len(sorted_ms) >= 20 else max(sorted_ms, default=0.0)

    return MetricsSummary(
        total_queries=len(traces),
        avg_total_ms=round(mean(total_ms_list), 2),
        avg_retrieval_ms=round(mean(retrieval_ms_list), 2),
        avg_llm_ms=round(mean(llm_ms_list), 2),
        abstention_rate=round(abstentions / len(traces), 4),
        avg_confidence=round(mean(confidence_list), 4),
        p50_ms=round(p50, 2),
        p95_ms=round(p95, 2),
    )
