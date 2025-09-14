import pytest
from httpx import AsyncClient
from app.main import app
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_tag_success(async_client: AsyncClient, async_session: AsyncSession):
    # Register and verify a user (simulate admin)
    user = User(
        name="Admin User",
        email="admin@example.com",
        matric_or_faculty_id="180404011",
        department="Computer Engineering",
        password_hash="fakehash",
        is_verified=True,
        is_active=True,
        account_status="active",
        role="admin"
    )
    async_session.add(user)
    await async_session.commit()
    # Simulate login and get token (bypass for test)
    headers = {"Authorization": "Bearer testtoken"}
    payload = {"name": "Test Tag", "category": "department"}
    response = await async_client.post("/tags", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]

@pytest.mark.asyncio
async def test_create_tag_duplicate(async_client: AsyncClient, async_session: AsyncSession):
    headers = {"Authorization": "Bearer testtoken"}
    payload = {"name": "Duplicate Tag", "category": "department"}
    await async_client.post("/tags", json=payload, headers=headers)
    response = await async_client.post("/tags", json=payload, headers=headers)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_approve_tag(async_client: AsyncClient, async_session: AsyncSession):
    headers = {"Authorization": "Bearer testtoken"}
    # Create tag
    payload = {"name": "Approve Tag", "category": "department"}
    tag_resp = await async_client.post("/tags", json=payload, headers=headers)
    tag_id = tag_resp.json()["id"]
    # Approve tag
    response = await async_client.patch(f"/tags/{tag_id}/approve", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

@pytest.mark.asyncio
async def test_reject_tag(async_client: AsyncClient, async_session: AsyncSession):
    headers = {"Authorization": "Bearer testtoken"}
    # Create tag
    payload = {"name": "Reject Tag", "category": "department"}
    tag_resp = await async_client.post("/tags", json=payload, headers=headers)
    tag_id = tag_resp.json()["id"]
    # Reject tag
    response = await async_client.patch(f"/tags/{tag_id}/reject", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected" 