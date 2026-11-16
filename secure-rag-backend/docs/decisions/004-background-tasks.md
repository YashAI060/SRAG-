# ADR-004: Background Tasks vs. Durable Queue

**Status**: Accepted (V1 — FastAPI BackgroundTasks)  
**Date**: 2026-09-02

## Context

Document ingestion is compute-intensive: PDF extraction, OCR, chunking, embedding API calls. It must not block the HTTP response.

## Decision

**V1**: FastAPI `BackgroundTasks` for ingestion.

The ingestion function (`_ingest_document`) is written as a plain Python function with no FastAPI coupling, so it can be moved to a Celery/RQ worker without rewriting the pipeline.

## Tradeoffs

| Approach | Pros | Cons |
|----------|------|------|
| FastAPI BackgroundTasks | Zero infra, simple | Lost on restart, no retry, no concurrency control |
| Celery + Redis | Durable, retryable, scalable | Adds 2 infrastructure components |
| RQ + Redis | Simpler than Celery | Still requires Redis |
| Cloud Queue (SQS/Pub-Sub) | Fully managed | Vendor lock-in |

## V1 Limitation (Documented)

If the server restarts during ingestion, the document status remains `processing` in the database. A startup reconciliation job can detect and re-queue stale `processing` documents. This is documented as a known MVP limitation.

## Migration to V2

```python
# V1 (current)
background_tasks.add_task(_ingest_document, ...)

# V2 (future)
celery_worker.apply_async(_ingest_document, args=[...])
```

The `_ingest_document` function signature does not change.
