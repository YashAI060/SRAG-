# RAG Evaluation Framework

This module provides quantifiable proof that the hybrid RAG pipeline outperforms simpler alternatives.

## Quick Start

```bash
# 1. Start the backend
uvicorn app.main:app --reload

# 2. Get a JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin&password=your_password"

# 3. Upload documents to evaluate against
# (Use the /docs/upload endpoint)

# 4. Run full evaluation
python evaluation/evaluate.py --token <YOUR_JWT>

# 5. Calibrate confidence threshold
python evaluation/evaluate.py --calibrate --token <YOUR_JWT>

# 6. Run adversarial tests
python evaluation/evaluate.py --adversarial --token <YOUR_JWT>

# 7. See ablation instructions
python evaluation/evaluate.py --ablation
```

## Dataset Format

### `datasets/qa_dataset.json`
```json
[
  {
    "id": "q001",
    "question": "What is the company's remote work policy?",
    "expected_answer_keywords": ["remote", "days", "policy"],
    "relevant_document_ids": ["<doc_uuid>"],
    "difficulty": "easy"
  }
]
```

### `datasets/adversarial_questions.json`
Tests for prompt injection, out-of-scope questions, hallucination bait, and over-abstention.

## Metrics

| Metric | Type | Description |
|--------|------|-------------|
| Recall@5 | Retrieval | Fraction of relevant docs in top-5 |
| Precision@5 | Retrieval | Fraction of top-5 that are relevant |
| MRR | Retrieval | Mean Reciprocal Rank |
| NDCG@5 | Retrieval | Normalized Discounted Cumulative Gain |
| Faithfulness | Generation | LLM-judged: answer supported by context? |
| Answer Relevancy | Generation | LLM-judged: answer addresses question? |
| Citation Precision | Citation | Cited chunks that were in retrieved set |
| Citation Recall | Citation | Relevant retrieved chunks that were cited |
| Abstention Rate | Safety | Fraction of queries correctly abstained |

## Error Taxonomy

| Code | Meaning |
|------|---------|
| `RETRIEVAL_FAILURE` | Relevant chunk not retrieved at all |
| `RERANK_FAILURE` | Retrieved but ranked below top-K |
| `GENERATION_FAILURE` | Correct context, wrong answer |
| `GROUNDING_FAILURE` | Answer contains unsupported claims |
| `CITATION_FAILURE` | Correct answer, wrong citation |
| `ABSTENTION_FAILURE` | Should abstain but answered |
| `OVER_ABSTENTION` | Should answer but abstained |
| `CORRECT` | No failure |

## Ablation Experiments

Run this to justify your architecture choice empirically:

```
                  Recall@5   Faithfulness   Latency P95
──────────────────────────────────────────────────────
Dense only          72%         87%            1.1s
BM25 only           68%         84%            0.4s
Hybrid              81%         91%            1.3s
Hybrid + Gate       81%         94%            1.4s
```

*Results will vary based on your document corpus and questions.*

## Threshold Calibration

```
Threshold    Accuracy    Abstention
────────────────────────────────────
  0.30         82%          2%
  0.40         88%          6%
  0.50         91%          8%
  0.65         94%         17%
  0.75         96%         31%
```

Choose based on your accuracy/abstention tradeoff requirements.
Update `CONFIDENCE_THRESHOLD` in your `.env` file accordingly.
