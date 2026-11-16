import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_rag_query_unauthorized():
    """Verify that chat queries are rejected without a valid JWT token."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        query_payload = {
            "prompt": "How are database secrets managed?",
            "stream": False
        }
        response = await ac.post("/api/chat/query", json=query_payload)
        assert response.status_code == 401
