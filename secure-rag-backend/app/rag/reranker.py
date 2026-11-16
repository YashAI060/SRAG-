"""
LLM-based reranker using Gemini as a single batched scoring call.

Architecture note (see ADR-005):
    This is an LLM-based reranker, NOT a traditional cross-encoder.
    A cross-encoder processes [query, document] pairs through a dedicated
    bi-encoder fine-tuned for relevance. Gemini acts as an LLM judge that
    reasons about relevance in a single batched prompt.

    Tradeoff vs local cross-encoder (e.g. ms-marco-MiniLM):
        + No extra model weights (~120MB+ for cross-encoder)
        + Can leverage Gemini's language understanding
        - Higher latency (network call)
        - Higher cost per query
        - Non-deterministic (sampling-based)
        - Potential rate-limiting

Single batched call design:
    Instead of N calls (one per chunk), we send ALL chunks in ONE prompt
    and request a JSON ranking. This is critical: N separate calls would be
    prohibitively slow and expensive for production use.
"""
import json
import logging
import requests
from typing import Optional

import google.generativeai as genai

from app.core.config import settings

import time
import logging
from typing import Optional, Tuple
from google.api_core.exceptions import (
    ResourceExhausted, 
    DeadlineExceeded,
    InternalServerError,
    ServiceUnavailable
)
from app.models.schemas import RerankerTrace

logger = logging.getLogger(__name__)

class LLMReranker:
    """
    Reranks a list of chunks against a query using a single batched Gemini call.

    Sends all candidate chunks in one request and parses a JSON ranking response.
    Falls back to rrf_score ordering if the LLM call fails.
    """

    def __init__(self):
        self.model = genai.GenerativeModel(settings.GENERATION_MODEL)

    def rerank(self, query: str, chunks: list[dict], top_k: int) -> Tuple[list[dict], RerankerTrace]:
        """
        Reranks chunks in a single batched LLM call.

        Parameters
        ----------
        query  : the user query
        chunks : list of chunk dicts, each with at minimum 'chunk_id' and 'text'
        top_k  : number of top chunks to return

        Returns
        -------
        Tuple of (Reranked list, RerankerTrace telemetry)
        Falls back to rrf_score ordering on any error.
        """
        start_time = time.perf_counter()
        if not chunks:
            trace = RerankerTrace(
                provider="none",
                status="skipped",
                attempts=0,
                latency_ms=0.0
            )
            return [], trace

        candidates = "\n\n".join(
            f"[{i+1}] chunk_id={c.get('chunk_id', str(i))}\n{c.get('text', '')[:400]}"
            for i, c in enumerate(chunks)
        )

        prompt = (
            f"You are a relevance ranker. Given the QUERY and CANDIDATE CHUNKS below, "
            f"score each chunk's relevance to the query on a 0.0–1.0 scale.\n\n"
            f"QUERY: {query}\n\n"
            f"CANDIDATE CHUNKS:\n{candidates}\n\n"
            f"Return ONLY a JSON object with key 'rankings', a list of objects each with "
            f"'chunk_id' and 'score'. Include every candidate. Example:\n"
            f'{{"rankings": [{{"chunk_id": "abc", "score": 0.92}}, ...]}}'
        )
        
        attempts = 0
        max_retries = settings.LLM_MAX_RETRIES
        delay = settings.LLM_RETRY_BASE_DELAY
        timeout = settings.LLM_TIMEOUT_SECONDS

        while attempts <= max_retries:
            attempts += 1
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"},
                    request_options={"timeout": timeout},
                )
                result = json.loads(response.text)
                rankings = result.get("rankings", [])

                # Build a score map from the LLM response
                score_map: dict[str, float] = {
                    r["chunk_id"]: float(r.get("score", 0.0))
                    for r in rankings
                    if "chunk_id" in r
                }

                # Apply scores back to chunks
                for chunk in chunks:
                    cid = chunk.get("chunk_id", "")
                    llm_score = score_map.get(cid, chunk.get("rrf_score", 0.0))
                    chunk["score"] = llm_score
                    chunk["reranker_score"] = llm_score

                reranked = sorted(chunks, key=lambda x: x.get("score", 0.0), reverse=True)
                latency_ms = (time.perf_counter() - start_time) * 1000
                
                trace = RerankerTrace(
                    provider="gemini",
                    status="success",
                    attempts=attempts,
                    latency_ms=latency_ms
                )
                return reranked[:top_k], trace
                
            except (ResourceExhausted, InternalServerError, ServiceUnavailable, requests.exceptions.RequestException) as e:
                logger.warning(f"LLM reranker attempt {attempts} failed (transient): {e}")
                if attempts <= max_retries:
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error("LLM reranker max retries exceeded.", exc_info=True)
                    break
            except (DeadlineExceeded, requests.exceptions.Timeout) as e:
                logger.warning(f"LLM reranker attempt {attempts} failed (timeout): {e}")
                if attempts <= 1: # Limited retry for timeouts
                    time.sleep(delay)
                else:
                    logger.error("LLM reranker timeout limits exceeded.", exc_info=True)
                    break
            except Exception as e:
                logger.error(f"LLM reranker failed with non-retryable exception: {e}", exc_info=True)
                break
                
        # Graceful fallback: use dense_score (cosine similarity, ~0.4–0.9)
        # NOT rrf_score (~0.016–0.033) which would collapse confidence gate signals.
        for chunk in chunks:
            fallback_score = chunk.get("dense_score") or chunk.get("rrf_score", 0.0)
            chunk["score"] = fallback_score
            chunk["reranker_score"] = fallback_score
            
        latency_ms = (time.perf_counter() - start_time) * 1000
        trace = RerankerTrace(
            provider="gemini",
            status="error",
            attempts=attempts,
            fallback="dense_score",
            fallback_reason="max_retries_exceeded",
            latency_ms=latency_ms
        )
        return sorted(chunks, key=lambda x: x.get("score", 0.0), reverse=True)[:top_k], trace


# Backward-compatible alias so imports like `from app.rag.reranker import CrossEncoderReranker`
# continue to work without changes elsewhere.
CrossEncoderReranker = LLMReranker
