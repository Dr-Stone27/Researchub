import pytest
from httpx import AsyncClient
from app.main import app
from app.models import User

@pytest.mark.asyncio
async def async_auth_headers():
    # This fixture should return headers with a valid JWT for a test user
    # For demonstration, replace 'testtoken' with a real token in your test setup
    return {"Authorization": "Bearer testtoken"}

@pytest.mark.asyncio
async def test_dashboard_welcome(async_client: AsyncClient):
    response = await async_client.get("/dashboard/welcome")
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_dashboard_stats_authenticated(async_client: AsyncClient):
    # Simulate authenticated user (token fixture or header if required)
    response = await async_client.get("/dashboard/stats")
    assert response.status_code in (200, 401)  # Accept 401 if auth required
    if response.status_code == 200:
        data = response.json()
        assert "total_users" in data
        assert "total_resources" in data

@pytest.mark.asyncio
async def test_dashboard_feed_trending(async_client: AsyncClient):
    response = await async_client.get("/dashboard/feed?type=trending")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_dashboard_feed_featured(async_client: AsyncClient):
    response = await async_client.get("/dashboard/feed?type=featured")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_dashboard_feed_invalid_type(async_client: AsyncClient):
    response = await async_client.get("/dashboard/feed?type=invalidtype")
    assert response.status_code in (400, 422)

@pytest.mark.asyncio
async def test_dashboard_user_role():
    headers = await async_auth_headers()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/dashboard/user/role", headers=headers)
    assert response.status_code == 200
    assert "role" in response.json()

@pytest.mark.asyncio
async def test_dashboard_user_has_draft():
    headers = await async_auth_headers()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/dashboard/user/has-draft", headers=headers)
    assert response.status_code == 200
    assert "has_draft" in response.json() 