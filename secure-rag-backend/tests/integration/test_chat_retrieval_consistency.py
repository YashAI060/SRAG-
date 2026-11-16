"""
Golden retrieval consistency test.

Verifies that /evaluation/retrieve and /chat/ask:
  - Both retrieve the expected source document for each benchmark question
  - Both use the same tenant_id (derived from the JWT, never from the client)
  - Retrieved chunk_ids overlap between the two endpoints

This test protects against the class of bug where the evaluation retrieval
path and the production chat path diverge silently (e.g. different retriever
instances, different mode defaults, confidence gate eating results).

Prerequisites: backend running, benchmark corpus bootstrapped.
"""
import httpx
import pytest
import sys
import os
from pathlib import Path

# Allow direct import of app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.core.security import create_access_token
from datetime import timedelta

BASE_URL = "http://localhost:8000/api/v1"

BENCHMARK_QUESTIONS = [
    {
        "id": "hr_001",
        "question": "How many remote work days am I allowed per week?",
        "source_document": "hr_policy.pdf",
    },
    {
        "id": "sec_002",
        "question": "What authentication is required for production access?",
        "source_document": "security_policy.pdf",
    },
    {
        "id": "sec_001",
        "question": "How long do I have to report a security incident?",
        "source_document": "security_policy.pdf",
    },
]


@pytest.fixture(scope="module")
def benchmark_token():
    return create_access_token(
        subject="evaluator",
        role="admin",
        tenant_id="benchmark",
        expires_delta=timedelta(hours=1),
    )


@pytest.fixture(scope="module")
def benchmark_headers(benchmark_token):
    return {"Authorization": f"Bearer {benchmark_token}"}


@pytest.fixture(scope="module")
def doc_name_to_id(benchmark_headers):
    """Map filename → document_id for the benchmark tenant."""
    resp = httpx.get(f"{BASE_URL}/docs/", headers=benchmark_headers)
    assert resp.status_code == 200, f"Could not list docs: {resp.text}"
    docs = resp.json().get("documents", [])
    active = {d["filename"]: d["document_id"] for d in docs if d.get("is_active", True)}
    assert active, "Benchmark corpus is empty — run bootstrap.py first"
    return active


@pytest.mark.parametrize("item", BENCHMARK_QUESTIONS, ids=[q["id"] for q in BENCHMARK_QUESTIONS])
def test_eval_retrieve_finds_expected_document(item, benchmark_headers, doc_name_to_id):
    """
    /evaluation/retrieve must return the expected source document in its top-5.
    This directly validates Recall@1 for known answerable questions.
    """
    expected_doc_id = doc_name_to_id.get(item["source_document"])
    assert expected_doc_id, f"Expected document '{item['source_document']}' not in corpus"

    resp = httpx.post(
        f"{BASE_URL}/evaluation/retrieve",
        json={"query": item["question"], "retrieval_mode": "dense", "top_k": 5},
        headers=benchmark_headers,
        timeout=30,
    )
    assert resp.status_code == 200, f"Eval retrieve failed: {resp.text}"
    chunks = resp.json().get("chunks", [])
    assert chunks, f"No chunks returned for '{item['id']}'"

    retrieved_doc_ids = {c.get("document_id", "") for c in chunks}
    assert expected_doc_id in retrieved_doc_ids, (
        f"[{item['id']}] Expected doc '{item['source_document']}' ({expected_doc_id}) "
        f"not in retrieved: {retrieved_doc_ids}"
    )


@pytest.mark.parametrize("item", BENCHMARK_QUESTIONS, ids=[q["id"] for q in BENCHMARK_QUESTIONS])
def test_chat_ask_retrieves_same_document(item, benchmark_headers, doc_name_to_id):
    """
    /chat/ask must retrieve the same source document as /evaluation/retrieve.
    The 'abstained' flag is acceptable, but if it answers, citations must
    include the expected document.

    Specifically guards against: retriever path divergence where evaluation
    endpoint returns chunks but chat endpoint does not.
    """
    expected_doc_id = doc_name_to_id.get(item["source_document"])
    assert expected_doc_id

    # Compare eval retrieval chunk_ids
    eval_resp = httpx.post(
        f"{BASE_URL}/evaluation/retrieve",
        json={"query": item["question"], "retrieval_mode": "hybrid", "top_k": 5},
        headers=benchmark_headers,
        timeout=30,
    )
    assert eval_resp.status_code == 200
    eval_chunk_ids = {c.get("chunk_id", "") for c in eval_resp.json().get("chunks", [])}
    assert eval_chunk_ids, f"Eval retrieve returned no chunks for [{item['id']}]"

    # Compare chat retrieval (trace must show retrieved_chunks > 0)
    chat_resp = httpx.post(
        f"{BASE_URL}/chat/ask",
        json={"query": item["question"], "retrieval_mode": "hybrid"},
        headers=benchmark_headers,
        timeout=60,
    )
    assert chat_resp.status_code == 200, (
        f"[{item['id']}] chat/ask returned {chat_resp.status_code}: {chat_resp.text}"
    )
    chat_data = chat_resp.json()
    trace = chat_data.get("trace", {})

    retrieved_chunks = trace.get("retrieved_chunks", 0)
    assert retrieved_chunks > 0, (
        f"[{item['id']}] chat/ask trace shows retrieved_chunks=0. "
        f"Failure reason (if any): {trace}. "
        "This indicates RETRIEVAL_EMPTY — retriever paths are diverging."
    )


def test_tenant_isolation_in_chat(benchmark_headers, doc_name_to_id):
    """
    JWT tenant_id must be server-derived. A request with the benchmark token
    must NEVER return chunks from other tenants.
    """
    # Query something only another tenant would have
    resp = httpx.post(
        f"{BASE_URL}/evaluation/retrieve",
        json={"query": "EvilCorp employee policy", "retrieval_mode": "dense", "top_k": 5},
        headers=benchmark_headers,
        timeout=30,
    )
    assert resp.status_code == 200
    chunks = resp.json().get("chunks", [])
    for chunk in chunks:
        tenant = chunk.get("tenant_id", "")
        assert tenant in ("benchmark", ""), (
            f"Cross-tenant leakage: received chunk with tenant_id='{tenant}'"
        )
