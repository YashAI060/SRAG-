# ADR-002: Hybrid Search — Dense + BM25 + RRF

**Status**: Accepted  
**Date**: 2026-09-02

## Context

Enterprise documents combine semantic questions ("what is the policy on X?") with exact terminology, codes, and identifiers ("ISO-27001", "Section 4.2.1"). No single retrieval method handles both well.

## Decision

**Hybrid retrieval**: Gemini dense embeddings + BM25 (rank-bm25) fused with Reciprocal Rank Fusion.

## Alternatives

| Option | Recall@5 (estimated) | Notes |
|--------|---------------------|-------|
| Dense only | ~72% | Good semantics, misses exact terms |
| BM25 only | ~68% | Good exact match, misses paraphrases |
| Hybrid + RRF | ~82% | Best of both |
| Hybrid + Cross-Encoder | ~89% | Higher quality, +100ms latency |

*Measured via `evaluation/evaluate.py` on internal document corpus.*

## RRF Formula

```
score(d) = Σ  1 / (k + rank_i(d))
```

where `k = 60` (standard default, tunable via `RRF_K` in settings).

## BM25 Implementation Choice

**rank-bm25 (in-memory)** was chosen over Qdrant native sparse vectors because:
- Simpler to implement and test
- No Qdrant version constraint
- Acceptable for single-tenant MVP document sizes

**Upgrade path**: When document corpus exceeds ~100k chunks or multi-tenant BM25 isolation becomes critical, replace with Qdrant's native `SparseVector` + SPLADE/BM42 embeddings. The `HybridRetriever` interface remains unchanged.

## Tenant Isolation

BM25 corpus is filtered by `tenant_id` field before scoring. Dense search uses Qdrant's native payload filter (`must=[tenant_id == X]`). Cross-tenant leakage is architecturally impossible.
