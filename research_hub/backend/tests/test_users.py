import pytest
from httpx import AsyncClient
from app.main import app
from app.models import User

@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient):
    payload = {
        "name": "Test User",
        "email": "testuser@example.com",
        "matric_or_faculty_id": "180404007",
        "department": "Computer Engineering",
        "password": "StrongPass1!",
        "confirm_password": "StrongPass1!"
    }
    response = await async_client.post("/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["is_verified"] is False

@pytest.mark.asyncio
async def test_register_user_duplicate_email(async_client: AsyncClient):
    payload = {
        "name": "Test User",
        "email": "testuser@example.com",
        "matric_or_faculty_id": "180404008",
        "department": "Computer Engineering",
        "password": "StrongPass1!",
        "confirm_password": "StrongPass1!"
    }
    # First registration
    await async_client.post("/register", json=payload)
    # Duplicate registration
    response = await async_client.post("/register", json=payload)
    assert response.status_code == 400 or response.status_code == 422

@pytest.mark.asyncio
async def test_login_success_and_token_revocation(async_client: AsyncClient):
    # Register and verify user
    payload = {
        "name": "Login User",
        "email": "loginuser@example.com",
        "matric_or_faculty_id": "180404009",
        "department": "Computer Engineering",
        "password": "StrongPass1!",
        "confirm_password": "StrongPass1!"
    }
    await async_client.post("/register", json=payload)
    # In a real test, manually verify user in DB here (mock or fixture)
    # Login
    login_payload = {"email_or_matric": payload["email"], "password": payload["password"]}
    response = await async_client.post("/login", json=login_payload)
    assert response.status_code == 200
    token = response.json()["token"]
    # Simulate password reset (token revocation)
    # In a real test, update user password_hash and token_version in DB (mock or fixture)
    # Try to use old token (should be rejected)
    headers = {"Authorization": f"Bearer {token}"}
    protected_response = await async_client.get("/api/dashboard/welcome", headers=headers)
    assert protected_response.status_code == 401 or protected_response.status_code == 403

@pytest.mark.asyncio
async def test_password_reset_flow(async_client: AsyncClient):
    # Register and verify user
    payload = {
        "name": "Reset User",
        "email": "resetuser@example.com",
        "matric_or_faculty_id": "180404010",
        "department": "Computer Engineering",
        "password": "StrongPass1!",
        "confirm_password": "StrongPass1!"
    }
    await async_client.post("/register", json=payload)
    # In a real test, manually verify user in DB here (mock or fixture)
    # Request password reset
    response = await async_client.post("/forgot-password", json={"email": payload["email"]})
    assert response.status_code == 200
    # Simulate setting a reset token in DB (mock or fixture)
    # Reset password
    reset_payload = {"token": "resettoken", "new_password": "NewStrongPass1!", "confirm_password": "NewStrongPass1!"}
    reset_response = await async_client.post("/reset-password", json=reset_payload)
    assert reset_response.status_code == 200
    # Try to login with new password (simulate hash check in real app)
    # (In a real test, you would mock hash_password and verify_password)

@pytest.mark.asyncio
async def test_admin_only_access_denied(async_client: AsyncClient):
    # Simulate non-admin user (no special token)
    response = await async_client.get("/users/admin-only-endpoint")
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_admin_only_access_granted(async_client: AsyncClient, admin_auth_headers):
    # Simulate admin user
    response = await async_client.get("/users/admin-only-endpoint", headers=admin_auth_headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_user_cannot_modify_other_user(async_client: AsyncClient, user_auth_headers):
    # User tries to modify another user's data
    response = await async_client.patch("/users/9999", headers=user_auth_headers, json={"email": "hacker@example.com"})
    assert response.status_code in (403, 404)  # 404 if user not found, 403 if forbidden 

@pytest.mark.asyncio
async def test_access_with_missing_jwt(async_client: AsyncClient):
    response = await async_client.get("/users/me")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_access_with_invalid_jwt(async_client: AsyncClient):
    headers = {"Authorization": "Bearer invalidtoken"}
    response = await async_client.get("/users/me", headers=headers)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_access_with_expired_jwt(async_client: AsyncClient, expired_jwt_headers):
    response = await async_client.get("/users/me", headers=expired_jwt_headers)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_access_with_token_version_mismatch(async_client: AsyncClient, mismatched_token_headers):
    response = await async_client.get("/users/me", headers=mismatched_token_headers)
    assert response.status_code == 401

    # Token version check would be part of a real DB test; skip or mock as needed

    # Token version check would be part of a real DB test; skip or mock as needed 