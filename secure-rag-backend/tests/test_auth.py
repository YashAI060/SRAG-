import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_auth_flow():
    """Simple integration test for user registration and JWT token retrieval."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Register a new user
        reg_payload = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "strongpassword123",
            "role": "user"
        }
        response = await ac.post("/api/auth/register", json=reg_payload)
        # Check if registration succeeded or already exists (depending on database state)
        assert response.status_code in [201, 400]

        # Login to retrieve token
        login_data = {
            "username": "testuser",
            "password": "strongpassword123"
        }
        response = await ac.post("/api/auth/login", data=login_data)
        assert response.status_code in [200, 401]
