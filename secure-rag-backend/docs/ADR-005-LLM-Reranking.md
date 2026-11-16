# ADR 005: LLM-Based Reranking via Gemini Flash

## Status
Accepted

## Context
In our Retrieval-Augmented Generation (RAG) pipeline, high precision in retrieved contexts is critical for mitigating hallucinations. After an initial hybrid retrieval step (dense vectors + BM25 keyword search), a reranking stage is used to refine the candidate chunks before they are sent to the final LLM generator. 

Initially, the design called for a traditional cross-encoder model (e.g., `ms-marco-MiniLM-L-6-v2`) which evaluates query-document pairs to produce a relevance score. A true cross-encoder takes the form:
`Query + Document → Cross-Encoder Model → Relevance Score`

However, to minimize the backend footprint and leverage our existing integration with Google's Gemini API, we opted to use an LLM-based reranking approach instead. Our current implementation passes the query and document chunks to `gemini-3.6-flash`, which acts as a judge to assign a relevance score.
This architecture looks like:
`Query + Document Chunks → Gemini Flash → Relevance Judgment / Score`

## Decision
We have decided to use **LLM-based reranking (via Gemini Flash)** instead of deploying a local, dedicated cross-encoder model for the reranking stage. We explicitly categorize this as "LLM Reranking" rather than "Cross-Encoder Reranking" to maintain architectural accuracy.

## Consequences
### Positive (Tradeoffs chosen)
* **Reduced Infrastructure Complexity:** We avoid having to host, load, and manage an additional local transformer model (which would require GPU resources or high memory/CPU usage) by offloading the task to a cloud LLM.
* **Reasoning Capabilities:** An LLM can perform more complex reasoning about *why* a chunk is relevant to a query, potentially handling nuanced semantic relationships better than smaller cross-encoder models.
* **Unified Provider:** Leverages our existing dependency on the Gemini API.

### Negative
* **Latency:** Calling a cloud LLM API for reranking introduces network latency and is significantly slower per-query than running a small, optimized local cross-encoder model.
* **Rate Limits:** As observed in our integration tests, querying the Gemini free tier can quickly hit the 15 RPM rate limit, causing 429 Quota Exceeded errors. Production usage would require a paid tier to handle concurrent user load.
* **Cost:** API-based reranking incurs a token cost for every candidate chunk evaluated, unlike a locally hosted open-source model.

## Alternatives Considered
* **Local Cross-Encoder (e.g., `ms-marco-MiniLM-L-6-v2`)**: This would provide faster, cheaper reranking without rate limits. However, we opted for the LLM-based approach to reduce local deployment overhead for the MVP and evaluate the reasoning capabilities of Gemini Flash as a reranker. We may switch to a local model if API costs or latency become prohibitive at scale.
