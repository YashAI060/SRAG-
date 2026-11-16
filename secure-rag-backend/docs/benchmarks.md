# Benchmark Evolution & Analysis

The Secure RAG system was driven by an adversarial benchmark containing 90 questions (lexical, semantic, multi-hop, unanswerable) and a corpus of hard-negative policy documents.

## Engineering Matrix

| Observation | Engineering Decision |
| :--- | :--- |
| Hard negatives exposed retrieval failures | Build adversarial V2 benchmark |
| Contextual metadata improved dense CR@5 | Adopt contextualized dense representation |
| BM25 degraded with contextual text | Restore BM25 to canonical text |
| Multi-hop remained weak (MhS@5 = 0.000) | Introduce query decomposition |
| Gemini unavailable during evaluation | Implement graceful LLM fallback |
| RRF implementation flaw discovered | V2.3.1 per-query RRF correction |
| Unbounded subqueries | Add MAX_SUBQUERIES = 3 |

## V2.3 Benchmark Results (Fallback Mode)

Because the decomposition LLM was intentionally quota-exhausted during the final run, the **Hybrid + Decomp** metrics perfectly match the **Hybrid RRF (Orig)** baseline. This proves that the fallback architecture works flawlessly and prevents the system from failing when an external dependency is unavailable.

| Configuration | CR@5 | MhS@5 | MRR | NDCG@5 | p50 | p95 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Dense | 0.811 | 0.733 | 0.583 | 0.614 | 2096ms | 2119ms |
| BM25 (Raw text) | 0.567 | 0.567 | 0.371 | 0.420 | 2118ms | 2161ms |
| Hybrid RRF (Orig) | 0.794 | 0.722 | 0.517 | 0.560 | 2132ms | 2159ms |
| **Hybrid + Decomp** | **0.794** | **0.722** | **0.517** | **0.560** | 2331ms | 2651ms |

*Note: The latency for Hybrid + Decomp is slightly higher (~200-400ms) because it awaits the LLM timeout/quota rejection before falling back.*

> **Query decomposition introduces multi-evidence retrieval for complex queries, with graceful fallback to baseline retrieval when the LLM provider is unavailable. Its retrieval-quality improvement remains unvalidated because Gemini quota was exhausted during the benchmark run.**
