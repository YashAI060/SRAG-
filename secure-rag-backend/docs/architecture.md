# Architecture

## V2.3.1 Pipeline

```mermaid
flowchart TD
    UserQuery[User Query] --> Auth[API/Auth Boundary]
    Auth --> Decomp{Query Decomposition\nGemini optional}
    
    Decomp -- ACTIVE --> SubQs[Original +\nSubqueries]
    Decomp -- FALLBACK --> Orig[Original only]
    
    SubQs --> SearchBound[Tenant-Isolated Search]
    Orig --> SearchBound
    
    SearchBound --> Dense[Dense Search\ncontextualized text]
    SearchBound --> BM25[BM25 Search\nraw text]
    
    Dense --> RRF[Per-query RRF Fusion]
    BM25 --> RRF
    
    RRF --> Dedup[Deduplicate / Aggregate]
    Dedup --> TopK[Top-K]
    TopK --> Rerank[Rerank / Confidence]
    Rerank --> Gen[Grounded Generation]
    Gen --> Validate[Citation Validation]
    Validate --> Answer[Final Answer]
```

### Key Design Decisions
- **Contextualized vs. Canonical Text:** Dense embeddings use contextualized text (prepended with Document Title and Section) to improve semantic disambiguation. BM25 is strictly constrained to canonical raw text, as adding repeated metadata to the BM25 index degraded its performance.
- **Per-Query RRF Fusion:** When using query decomposition, each query branch (Original + Subqueries) independently assigns ranks (0 to K) to its retrieved hits before the RRF scores are globally aggregated by chunk ID. This prevents subquery hits from being unfairly penalized.
