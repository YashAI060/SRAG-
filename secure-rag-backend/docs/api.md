# API Documentation

## POST /api/v1/chat/ask

Submits a query to the RAG pipeline.

### Request
```bash
curl -X POST "http://localhost:8000/api/v1/chat/ask" \
     -H "Authorization: Bearer <TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
           "query": "What is the maximum remote work allowance for tier 1 employees?",
           "mode": "hybrid",
           "decompose": true
         }'
```

### Response (Normal with Telemetry)
```json
{
  "answer": "Tier 1 employees are allowed up to 4 weeks of remote work.",
  "citations": [
    {
      "chunk_id": "remote_001_c3",
      "text": "Tier 1 remote allowance is 4 weeks.",
      "page_number": 2,
      "filename": "remote_policy.pdf"
    }
  ],
  "trace": {
    "decomposition_status": "ACTIVE",
    "decomposition_latency_ms": 450.2,
    "subquery_count": 2,
    "subqueries_requested": 3,
    "subqueries_accepted": 2,
    "subqueries_truncated": false,
    "retrieval_latency_ms": 112.5,
    "llm_latency_ms": 850.1,
    "total_latency_ms": 1412.8,
    "retrieved_chunk_count": 5
  }
}
```

### Response (Fallback)
```json
{
  "answer": "Tier 1 employees are allowed up to 4 weeks of remote work.",
  "citations": [...],
  "trace": {
    "decomposition_status": "FALLBACK",
    "subquery_count": 0,
    "subqueries_requested": 0,
    "subqueries_accepted": 0,
    ...
  }
}
```

## POST /api/v1/evaluation/retrieve
Used for evaluating the retrieval performance. Returns only the retrieved chunks and telemetry.
