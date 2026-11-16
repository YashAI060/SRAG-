"""
Integration tests for document edge cases (empty, corrupted, duplicates, versioning, etc.).
"""
import io
import time
import pytest
import httpx
import uuid
import asyncio
from fpdf import FPDF

BASE_URL = "http://localhost:8000/api/v1"

# ── Helpers ───────────────────────────────────────────────────────────────────

def create_user_and_login(username: str, email: str) -> str:
    httpx.post(f"{BASE_URL}/auth/register", json={
        "username": username,
        "email": email,
        "password": "Password123",
        "role": "admin",
    })
    resp = httpx.post(f"{BASE_URL}/auth/login", data={
        "username": username,
        "password": "Password123",
    })
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    return resp.json()["access_token"]

@pytest.fixture(scope="module")
def tenant_a_token():
    uid = uuid.uuid4().hex[:6]
    return create_user_and_login(f"tenant_a_{uid}", f"tenant_a_{uid}@corp.com")

@pytest.fixture(scope="module")
def tenant_b_token():
    uid = uuid.uuid4().hex[:6]
    return create_user_and_login(f"tenant_b_{uid}", f"tenant_b_{uid}@corp.com")

@pytest.fixture
def headers_a(tenant_a_token):
    return {"Authorization": f"Bearer {tenant_a_token}"}

@pytest.fixture
def headers_b(tenant_b_token):
    return {"Authorization": f"Bearer {tenant_b_token}"}

def generate_pdf(text: str) -> bytes:
    # Ensure text is long enough to bypass OCR fallback (usually > 50 chars) if text is provided
    if text:
        padded_text = text + " " + ("This is some extra padding text to ensure the document has enough characters to avoid triggering the OCR fallback logic. " * 5)
    else:
        padded_text = ""
        
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    pdf.multi_cell(0, 10, text=padded_text, align="L")
    return bytes(pdf.output())

async def wait_for_status(headers: dict, doc_id: str, target_status: str, timeout: int = 30):
    start = time.time()
    while time.time() - start < timeout:
        r = httpx.get(f"{BASE_URL}/docs/{doc_id}", headers=headers)
        if r.status_code == 200:
            doc = r.json()
            if doc["status"] == target_status:
                return doc
            if doc["status"] == "failed" and target_status != "failed":
                pytest.fail(f"Document processing failed: {doc.get('error_message')}")
        await asyncio.sleep(2)
    pytest.fail(f"Timeout waiting for status {target_status}")

# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_pdf(headers_a):
    """1. Empty PDF: Ensure 400 or graceful fail."""
    empty_pdf_bytes = generate_pdf("")
    files = {"file": ("empty.pdf", empty_pdf_bytes, "application/pdf")}
    resp = httpx.post(f"{BASE_URL}/docs/upload", files=files, headers=headers_a)
    assert resp.status_code in (200, 202, 400)
    
    if resp.status_code in (200, 202):
        doc_id = resp.json()["document_id"]
        doc = await wait_for_status(headers_a, doc_id, "failed")
        assert doc["status"] == "failed"
        assert doc["chunk_count"] == 0

@pytest.mark.asyncio
async def test_corrupted_pdf(headers_a):
    """2. Corrupted PDF: Fails gracefully."""
    corrupt_bytes = b"%PDF-1.4\n%This is not a real PDF at all! Corrupted!!!"
    files = {"file": ("corrupt.pdf", corrupt_bytes, "application/pdf")}
    resp = httpx.post(f"{BASE_URL}/docs/upload", files=files, headers=headers_a)
    
    if resp.status_code in (200, 202):
        doc_id = resp.json()["document_id"]
        doc = await wait_for_status(headers_a, doc_id, "failed")
        assert doc["status"] == "failed"

@pytest.mark.asyncio
async def test_duplicate_upload(headers_a):
    """5. Duplicate upload: sequential identical uploads should not duplicate chunks."""
    content = generate_pdf("Unique test content for duplicate test.")
    
    # Upload 1
    resp1 = httpx.post(f"{BASE_URL}/docs/upload", files={"file": ("policy.pdf", content, "application/pdf")}, headers=headers_a)
    assert resp1.status_code in (200, 202)
    doc_id1 = resp1.json()["document_id"]
    await wait_for_status(headers_a, doc_id1, "ready")
    
    # Upload 2 (duplicate)
    resp2 = httpx.post(f"{BASE_URL}/docs/upload", files={"file": ("policy.pdf", content, "application/pdf")}, headers=headers_a)
    assert resp2.status_code in (200, 202)
    doc_id2 = resp2.json()["document_id"]
    
    # Wait to see what happens
    await wait_for_status(headers_a, doc_id2, "ready")
    
    # Check total documents for tenant A
    resp_list = httpx.get(f"{BASE_URL}/docs/", headers=headers_a)
    docs = [d for d in resp_list.json().get("documents", []) if d["filename"] == "policy.pdf"]
    
    eval_resp = httpx.post(f"{BASE_URL}/evaluation/retrieve", json={"query": "Unique test content for duplicate test.", "retrieval_mode": "dense"}, headers=headers_a, timeout=30.0)
    chunks = eval_resp.json().get("chunks", [])
    # Distinct chunk IDs
    unique_chunks = set(s["chunk_id"] for s in chunks)
    assert len(chunks) == len(unique_chunks), "Duplicate upload created duplicate chunks in index!"

@pytest.mark.asyncio
async def test_concurrent_duplicate_upload(headers_a):
    """9. Concurrent duplicate upload."""
    content = generate_pdf("Concurrency race condition test.")
    
    async def upload():
        async with httpx.AsyncClient() as client:
            return await client.post(f"{BASE_URL}/docs/upload", files={"file": ("race.pdf", content, "application/pdf")}, headers=headers_a)
            
    results = await asyncio.gather(upload(), upload())
    for r in results:
        assert r.status_code in (200, 202)
    
    # Wait for both
    for r in results:
        await wait_for_status(headers_a, r.json()["document_id"], "ready")
        
    eval_resp = httpx.post(f"{BASE_URL}/evaluation/retrieve", json={"query": "Concurrency race condition test.", "retrieval_mode": "dense"}, headers=headers_a)
    chunks = eval_resp.json().get("chunks", [])
    unique_chunks = set(s["chunk_id"] for s in chunks)
    assert len(chunks) == len(unique_chunks), "Concurrent upload created duplicate chunks!"

@pytest.mark.asyncio
async def test_versioning(headers_a):
    """6. Versioning: v2 active, v1 inactive."""
    v1_content = generate_pdf("This is version ONE of the handbook.")
    v2_content = generate_pdf("This is version TWO of the handbook.")
    
    # Upload v1
    resp1 = httpx.post(f"{BASE_URL}/docs/upload", files={"file": ("handbook.pdf", v1_content, "application/pdf")}, headers=headers_a)
    doc_id1 = resp1.json()["document_id"]
    await wait_for_status(headers_a, doc_id1, "ready")
    
    # Upload v2
    resp2 = httpx.post(f"{BASE_URL}/docs/upload", files={"file": ("handbook.pdf", v2_content, "application/pdf")}, headers=headers_a)
    doc_id2 = resp2.json()["document_id"]
    await wait_for_status(headers_a, doc_id2, "ready")
    
    doc1 = httpx.get(f"{BASE_URL}/docs/{doc_id1}", headers=headers_a).json()
    doc2 = httpx.get(f"{BASE_URL}/docs/{doc_id2}", headers=headers_a).json()
    
    # v1 should be inactive, v2 active
    assert not doc1.get("is_active", True), "v1 is still active!"
    assert doc2.get("is_active", True), "v2 is not active!"
    
    # Search should only find v2
    resp = httpx.post(f"{BASE_URL}/evaluation/retrieve", json={"query": "version of the handbook", "retrieval_mode": "dense"}, headers=headers_a)
    chunks = resp.json().get("chunks", [])
    context = " ".join([c.get("text", "") for c in chunks])
    assert "version TWO" in context
    assert "version ONE" not in context

@pytest.mark.asyncio
async def test_tenant_isolation(headers_a, headers_b):
    """7. Tenant Isolation with same filename and conflicting queries."""
    content_a = generate_pdf("Acme employees must use MFA.")
    content_b = generate_pdf("EvilCorp employees must use hardware keys.")
    
    # Upload A
    resp_a = httpx.post(f"{BASE_URL}/docs/upload", files={"file": ("security_policy.pdf", content_a, "application/pdf")}, headers=headers_a)
    doc_a = resp_a.json()["document_id"]
    await wait_for_status(headers_a, doc_a, "ready")
    
    # Upload B
    resp_b = httpx.post(f"{BASE_URL}/docs/upload", files={"file": ("security_policy.pdf", content_b, "application/pdf")}, headers=headers_b)
    doc_b = resp_b.json()["document_id"]
    await wait_for_status(headers_b, doc_b, "ready")
    
    # Query A for auth method
    eval_a = httpx.post(f"{BASE_URL}/evaluation/retrieve", json={"query": "What authentication method is required?", "retrieval_mode": "dense"}, headers=headers_a)
    assert eval_a.status_code == 200, f"Error: {eval_a.text}"
    context_a = " ".join([c.get("text", "") for c in eval_a.json().get("chunks", [])])
    assert "MFA" in context_a
    
    # Query B for auth method
    eval_b = httpx.post(f"{BASE_URL}/evaluation/retrieve", json={"query": "What authentication method is required?", "retrieval_mode": "dense"}, headers=headers_b)
    assert eval_b.status_code == 200, f"Error: {eval_b.text}"
    context_b = " ".join([c.get("text", "") for c in eval_b.json().get("chunks", [])])
    assert "hardware keys" in context_b
    
    # Deliberate breach attempt from A
    breach = httpx.post(f"{BASE_URL}/evaluation/retrieve", json={"query": "What does EvilCorp's policy say?", "retrieval_mode": "dense"}, headers=headers_a)
    assert breach.status_code == 200, f"Error: {breach.text}"
    context_breach = " ".join([c.get("text", "") for c in breach.json().get("chunks", [])])
    assert "hardware keys" not in context_breach, "Tenant A was able to read Tenant B's docs!"

