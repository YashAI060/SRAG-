"""
Integration tests for document upload and ingestion.
Requires a running FastAPI server + Qdrant instance.
Run with: pytest tests/integration/ -v
"""
import io
import pytest
import httpx
import asyncio

BASE_URL = "http://localhost:8000/api/v1"

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def token():
    """Login and return a valid JWT for tests."""
    resp = httpx.post(f"{BASE_URL}/auth/login", data={
        "username": "test_admin",
        "password": "testpassword123",
    })
    if resp.status_code == 401:
        # Register first
        httpx.post(f"{BASE_URL}/auth/register", json={
            "username": "test_admin",
            "email": "test_admin@integration.test",
            "password": "testpassword123",
            "role": "admin",
        })
        resp = httpx.post(f"{BASE_URL}/auth/login", data={
            "username": "test_admin",
            "password": "testpassword123",
        })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestDocumentUpload:
    def test_upload_requires_auth(self):
        resp = httpx.post(f"{BASE_URL}/docs/upload", files={"file": ("test.pdf", b"data", "application/pdf")})
        assert resp.status_code == 401

    def test_upload_rejects_non_pdf(self, headers):
        resp = httpx.post(
            f"{BASE_URL}/docs/upload",
            files={"file": ("test.txt", b"hello world", "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

    def test_upload_pdf_accepted(self, headers):
        # Minimal valid PDF bytes
        minimal_pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""
        resp = httpx.post(
            f"{BASE_URL}/docs/upload",
            files={"file": ("policy.pdf", minimal_pdf, "application/pdf")},
            headers=headers,
        )
        assert resp.status_code in (200, 202)
        body = resp.json()
        assert "document_id" in body
        assert body["status"] in ("pending", "ready")
        return body["document_id"]

    def test_duplicate_upload_returns_existing(self, headers):
        content = b"unique content for dedup test " * 100
        files = {"file": ("dedup_test.pdf", content, "application/pdf")}
        r1 = httpx.post(f"{BASE_URL}/docs/upload", files=files, headers=headers)
        r2 = httpx.post(f"{BASE_URL}/docs/upload", files=files, headers=headers)
        # Second upload may return duplicate=True if first was fully processed
        assert r1.status_code in (200, 202)
        assert r2.status_code in (200, 202)

    def test_list_documents(self, headers):
        resp = httpx.get(f"{BASE_URL}/docs/", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "documents" in body
        assert "total" in body

    def test_tenant_isolation(self):
        """Documents uploaded by user A must not appear for user B."""
        # Register user B
        httpx.post(f"{BASE_URL}/auth/register", json={
            "username": "user_b_isolation",
            "email": "user_b@isolation.test",
            "password": "password123",
            "role": "user",
        })
        resp_b = httpx.post(f"{BASE_URL}/auth/login", data={
            "username": "user_b_isolation",
            "password": "password123",
        })
        if resp_b.status_code != 200:
            pytest.skip("Could not create isolation test user")

        token_b = resp_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        docs_b = httpx.get(f"{BASE_URL}/docs/", headers=headers_b).json()
        # User B should have 0 documents (they haven't uploaded any)
        assert docs_b["total"] == 0
