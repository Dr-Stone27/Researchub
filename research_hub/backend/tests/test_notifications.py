import pytest
from httpx import AsyncClient
from app.main import app
from app.models import User, Notification

@pytest.mark.asyncio
async def notification_payload():
    return {
        "user_id": 1,
        "type": "system",
        "message": "Test notification.",
        "resource_id": None
    }

@pytest.mark.asyncio
async def test_create_notification(async_client: AsyncClient):
    payload = await notification_payload()
    response = await async_client.post("/notifications/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "system"
    assert data["message"] == "Test notification."
    assert data["is_read"] is False
    return data["id"]

@pytest.mark.asyncio
async def test_list_notifications(async_client: AsyncClient):
    response = await async_client.get("/notifications/?user_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_mark_notification_as_read(async_client: AsyncClient):
    # Create notification
    payload = await notification_payload()
    create_resp = await async_client.post("/notifications/", json=payload)
    notification_id = create_resp.json()["id"]
    # Mark as read
    response = await async_client.patch(f"/notifications/{notification_id}/read?is_read=true")
    assert response.status_code == 200
    assert response.json()["is_read"] is True

@pytest.mark.asyncio
async def test_delete_notification(async_client: AsyncClient):
    # Create notification
    payload = await notification_payload()
    create_resp = await async_client.post("/notifications/", json=payload)
    notification_id = create_resp.json()["id"]
    # Delete notification
    response = await async_client.delete(f"/notifications/{notification_id}")
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_delete_notification_not_found(async_client: AsyncClient):
    response = await async_client.delete("/notifications/99999")
    assert response.status_code == 404

# Mark as read/unread and delete would require a created notification id; typically handled in a more advanced test setup with fixtures or DB mocking. 