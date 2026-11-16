"""
RAG Evaluation Metrics.

Retrieval metrics:
    Recall@K        — fraction of relevant docs in top-K
    Precision@K     — fraction of top-K that are relevant
    MRR             — Mean Reciprocal Rank
    NDCG@K          — Normalized Discounted Cumulative Gain

Generation metrics:
    Faithfulness    — LLM-judged: is the answer supported by context?
    Answer Relevancy— LLM-judged: does the answer address the question?
    Citation Precision — fraction of cited chunks in retrieved set
    Citation Recall — fraction of retrieved relevant chunks actually cited

Error taxonomy:
    RETRIEVAL_FAILURE   — relevant chunk not retrieved
    RERANK_FAILURE      — retrieved but ranked below top-K
    GENERATION_FAILURE  — correct context, wrong answer
    GROUNDING_FAILURE   — answer contains unsupported claims
    CITATION_FAILURE    — correct answer, wrong citation
    ABSTENTION_FAILURE  — should abstain but answered
    OVER_ABSTENTION     — should answer but abstained
"""
from __future__ import annotations

import math
from typing import Optional

import google.generativeai as genai

# ── Retrieval Metrics ─────────────────────────────────────────────────────────


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """Fraction of relevant docs found in top-K retrieved."""
    if not relevant_ids:
        return 1.0
    top_k = set(retrieved_ids[:k])
    return len(top_k & set(relevant_ids)) / len(relevant_ids)


def precision_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """Fraction of top-K retrieved that are relevant."""
    if k == 0:
        return 0.0
    top_k = retrieved_ids[:k]
    relevant_set = set(relevant_ids)
    return sum(1 for doc_id in top_k if doc_id in relevant_set) / k


def mrr(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """Mean Reciprocal Rank — reciprocal of rank of first relevant result."""
    relevant_set = set(relevant_ids)
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_set:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """Normalised Discounted Cumulative Gain @ K."""
    relevant_set = set(relevant_ids)

    def dcg(ids: list[str]) -> float:
        return sum(
            1.0 / math.log2(rank + 2)
            for rank, doc_id in enumerate(ids[:k])
            if doc_id in relevant_set
        )

    actual_dcg = dcg(retrieved_ids)
    ideal_dcg = dcg(list(relevant_ids)[:k])
    return actual_dcg / ideal_dcg if ideal_dcg > 0 else 0.0


# ── Generation Metrics ────────────────────────────────────────────────────────

_FAITHFULNESS_PROMPT = """You are an impartial evaluator.

CONTEXT:
{context}

QUESTION: {question}
ANSWER: {answer}

Is the answer fully supported by the context?
Reply with ONLY a JSON: {{"score": <0.0-1.0>, "reason": "<brief reason>"}}"""

_RELEVANCY_PROMPT = """You are an impartial evaluator.

QUESTION: {question}
ANSWER: {answer}

Does the answer directly address the question? (Ignore factual accuracy — just relevance.)
Reply with ONLY a JSON: {{"score": <0.0-1.0>, "reason": "<brief reason>"}}"""


def evaluate_faithfulness(
    question: str, answer: str, context: str, model_name: str = "gemini-2.5-flash"
) -> dict:
    """LLM-as-judge: is the answer grounded in the retrieved context?"""
    import json
    model = genai.GenerativeModel(model_name)
    try:
        resp = model.generate_content(
            _FAITHFULNESS_PROMPT.format(context=context, question=question, answer=answer)
        )
        return json.loads(resp.text.strip())
    except Exception as e:
        return {"score": 0.0, "reason": f"evaluation_error: {e}"}


def evaluate_answer_relevancy(
    question: str, answer: str, model_name: str = "gemini-2.5-flash"
) -> dict:
    """LLM-as-judge: does the answer address the question?"""
    import json
    model = genai.GenerativeModel(model_name)
    try:
        resp = model.generate_content(
            _RELEVANCY_PROMPT.format(question=question, answer=answer)
        )
        return json.loads(resp.text.strip())
    except Exception as e:
        return {"score": 0.0, "reason": f"evaluation_error: {e}"}


def citation_precision(
    cited_chunk_ids: list[str], retrieved_chunk_ids: list[str]
) -> float:
    if not cited_chunk_ids:
        return 1.0
    retrieved_set = set(retrieved_chunk_ids)
    valid = sum(1 for cid in cited_chunk_ids if cid in retrieved_set)
    return valid / len(cited_chunk_ids)


def citation_recall(
    cited_chunk_ids: list[str], relevant_chunk_ids: list[str]
) -> float:
    if not relevant_chunk_ids:
        return 1.0
    cited_set = set(cited_chunk_ids)
    covered = sum(1 for cid in relevant_chunk_ids if cid in cited_set)
    return covered / len(relevant_chunk_ids)


# ── Error Taxonomy ────────────────────────────────────────────────────────────

ERROR_TYPES = [
    "RETRIEVAL_FAILURE",    # Relevant chunk not retrieved
    "RERANK_FAILURE",       # Retrieved but ranked below top-K used
    "GENERATION_FAILURE",   # Correct context, wrong answer
    "GROUNDING_FAILURE",    # Answer contains unsupported claims
    "CITATION_FAILURE",     # Correct answer, wrong citation
    "ABSTENTION_FAILURE",   # Should abstain but answered
    "OVER_ABSTENTION",      # Should answer but abstained
    "CORRECT",              # No failure
]


def classify_error(
    retrieved_relevant: bool,
    ranked_in_top_k: bool,
    answer_correct: bool,
    answer_grounded: bool,
    citation_correct: bool,
    expected_abstain: bool,
    actual_abstained: bool,
) -> str:
    if expected_abstain and not actual_abstained:
        return "ABSTENTION_FAILURE"
    if not expected_abstain and actual_abstained:
        return "OVER_ABSTENTION"
    if not retrieved_relevant:
        return "RETRIEVAL_FAILURE"
    if retrieved_relevant and not ranked_in_top_k:
        return "RERANK_FAILURE"
    if not answer_grounded:
        return "GROUNDING_FAILURE"
    if not answer_correct:
        return "GENERATION_FAILURE"
    if not citation_correct:
        return "CITATION_FAILURE"
    return "CORRECT"
