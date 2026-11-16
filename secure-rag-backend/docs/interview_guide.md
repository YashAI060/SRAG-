# Interview Guide

## Architecture

**Why hybrid retrieval (Dense + BM25)?**
Dense retrieval is excellent for semantic concepts ("remote work"), but struggles with specific entities, IDs, or exact phrasing ("Tier 1 allowance"). BM25 excels at exact keyword matching. Combining them covers both recall patterns.

**Why RRF (Reciprocal Rank Fusion)?**
BM25 and Dense vector scores are on completely different mathematical scales (Cosine similarity vs. TF-IDF variations). RRF fuses them by ranking (1/k+rank), which doesn't require complex statistical calibration or score normalization.

**Why contextualized embeddings?**
During V2.1 evaluation, the dense retriever struggled with document disambiguation because many enterprise policy documents have identical boilerplate paragraphs (e.g., "Approval Authority" on Page 4). By appending the Document Title and Section Header to the chunk *before* embedding it, we contextualized the text.

**Why keep canonical text separately for BM25?**
We discovered that adding the Document Title to every chunk artificially degraded BM25 performance. It caused keyword saturation; every chunk suddenly matched the query just because it shared the title keywords. Therefore, we preserve the raw canonical text solely for the BM25 index.

**Why query decomposition?**
The evaluation proved that our Multi-hop Success Rate (MhS@5) was 0.000. The retriever could find individual evidence but couldn't retrieve all required evidence units simultaneously for a complex question. Decomposition splits a complex query into atomic information needs.

**Why not simply increase Top-K?**
Increasing Top-K degrades the generation LLM's performance (the "lost in the middle" phenomenon) and increases token costs. We wanted to improve the *density of relevance* in the top 5 chunks, not just flood the context window.

## Evaluation

**Why was V2.1 (Adversarial Benchmark) necessary?**
The initial testing showed Recall@5 saturated at 1.00. This meant the corpus was too easy. We needed semantic and lexical hard negatives (e.g., "Remote Work Policy" vs. "Remote Work Hardware Allowance") to actually measure retrieval precision.

**Why measure multi-hop success separately?**
Standard Recall measures if *any* relevant chunk was found. Multi-hop questions require *all* relevant chunks to synthesize an answer. If we didn't track it separately, the high overall Recall@5 would have hidden the complete failure on complex queries.

## Production & Safety

**What happens if Gemini returns 429 or times out during decomposition?**
The system catches `ResourceExhausted` and `DeadlineExceeded`, logs the failure, and degrades gracefully by executing the original user query through the standard hybrid retrieval pipeline. We validated this by running a full 90-question benchmark during a quota outage, maintaining 100% availability.

**What prevents unlimited subqueries?**
The application code enforces a hard `MAX_SUBQUERIES = 3` slice *after* parsing the LLM's JSON and deduplicating the list. The LLM prompt is treated merely as guidance; the application code is the security boundary.

**Tell me about a bug you discovered in your retrieval system.**
Our initial V2.3 fusion concatenated results from multiple query branches before assigning RRF ranks. That meant later subquery results started at artificially lower ranks (e.g., Rank 5 instead of Rank 0). We identified the issue through an engineering audit and changed the fusion algorithm to assign independent ranks per query branch before aggregating by chunk ID.
