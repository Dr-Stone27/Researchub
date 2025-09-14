import pytest
from httpx import AsyncClient
from app.main import app
from app.models import User
from app.utils import search_resources

@pytest.mark.asyncio
async def resource_payload():
    return {
        "title": "Test Guide",
        "description": "A test guide resource.",
        "type": "guide",
        "content_url": "http://example.com/guide.pdf",
        "created_by": 1,
        "tag_ids": []
    }

@pytest.mark.asyncio
async def test_create_resource(async_client: AsyncClient):
    payload = await resource_payload()
    response = await async_client.post("/resources/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Guide"
    assert data["type"] == "guide"
    return data["id"]

@pytest.mark.asyncio
async def test_list_resources(async_client: AsyncClient):
    response = await async_client.get("/resources/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_update_resource(async_client: AsyncClient):
    # Create resource
    payload = await resource_payload()
    create_resp = await async_client.post("/resources/", json=payload)
    resource_id = create_resp.json()["id"]
    update_payload = payload.copy()
    update_payload["title"] = "Updated Guide"
    response = await async_client.put(f"/resources/{resource_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Guide"

@pytest.mark.asyncio
async def test_update_resource_not_found(async_client: AsyncClient):
    update_payload = await resource_payload()
    response = await async_client.put("/resources/99999", json=update_payload)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_resource(async_client: AsyncClient):
    payload = await resource_payload()
    create_resp = await async_client.post("/resources/", json=payload)
    resource_id = create_resp.json()["id"]
    response = await async_client.delete(f"/resources/{resource_id}")
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_delete_resource_not_found(async_client: AsyncClient):
    response = await async_client.delete("/resources/99999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_search_resources_stub():
    results = search_resources("test")
    assert isinstance(results, list)
    assert results == []

@pytest.mark.asyncio
async def test_library_browse(async_client: AsyncClient):
    response = await async_client.get("/library/browse")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_library_search(async_client: AsyncClient):
    response = await async_client.get("/library/search?q=test")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_library_download_not_found(async_client: AsyncClient):
    response = await async_client.get("/library/99999/download")
    assert response.status_code in (404, 400)  # 404 if not found, 400 if invalid 

@pytest.mark.asyncio
async def research_submission_payload():
    return {
        "title": "Test Submission",
        "abstract": "A test research submission.",
        "authors": ["Test Author"],
        "department": "Computer Engineering",
        "file_url": "http://example.com/research.pdf",
        "submitted_by": 1
    }

@pytest.mark.asyncio
async def test_create_research_submission(async_client: AsyncClient):
    payload = await research_submission_payload()
    response = await async_client.post("/submissions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == payload["title"]
    return data["id"]

@pytest.mark.asyncio
async def test_list_research_submissions(async_client: AsyncClient):
    response = await async_client.get("/submissions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_research_submission_by_id_not_found(async_client: AsyncClient):
    response = await async_client.get("/submissions/99999")
    assert response.status_code == 404 

@pytest.mark.asyncio
async def guide_payload():
    return {
        "title": "Test Guide",
        "description": "A test guide resource.",
        "type": "guide",
        "content_url": "http://example.com/guide.pdf",
        "created_by": 1,
        "tag_ids": []
    }

@pytest.mark.asyncio
async def test_create_guide(async_client: AsyncClient):
    payload = await guide_payload()
    response = await async_client.post("/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == payload["title"]
    return data["id"]

@pytest.mark.asyncio
async def test_list_guides(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_guide_by_id_not_found(async_client: AsyncClient):
    response = await async_client.get("/99999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_guide_not_found(async_client: AsyncClient):
    payload = await guide_payload()
    response = await async_client.put("/99999", json=payload)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_guide_not_found(async_client: AsyncClient):
    response = await async_client.delete("/99999")
    assert response.status_code == 404 