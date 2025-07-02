"""
guides.py

API endpoints for managing resources (guides, templates, etc.) in the Research Resource Hub backend.
All endpoints and helper functions are async for scalability and auditability.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from .. import models, schemas, crud, database
from app.auth import verify_access_token, get_current_user
from app.database import get_db

router = APIRouter(
    prefix="/resources",
    tags=["Resources"]
)

# Helper to extract tag IDs from resource schema
def get_tag_ids(resource: schemas.ResourceCreate):
    """Extract tag IDs from a ResourceCreate schema, if present."""
    return resource.tag_ids if hasattr(resource, 'tag_ids') else None

async def get_current_user(Authorization: str = Header(...), db: AsyncSession = Depends(get_db)):
    """
    Async: Extract and validate the current user from the JWT token in the Authorization header.
    Raises HTTPException if token is missing, invalid, or user not found.
    """
    if not Authorization or not Authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    token = Authorization.split(" ", 1)[1]
    payload = verify_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user_id = int(payload["sub"])
    from sqlalchemy import select
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    user = result.scalars().first()
    if not user or not user.is_active or not user.is_verified or user.account_status != "active":
        raise HTTPException(status_code=403, detail="User account is not active or verified.")
    return user

@router.post("/", response_model=schemas.Resource)
async def create_resource(resource: schemas.ResourceCreate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Async: Create a new resource (guide, template, etc.).
    """
    tag_ids = get_tag_ids(resource)
    db_resource = await crud.create_resource(db, resource.dict(exclude={"tag_ids"}), tag_ids=tag_ids)
    return db_resource

@router.get("/{resource_id}", response_model=schemas.Resource)
async def get_resource(resource_id: int, db: AsyncSession = Depends(get_db)):
    """
    Async: Retrieve a resource by its ID.
    """
    db_resource = await crud.get_resource_by_id(db, resource_id)
    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return db_resource

@router.get("/", response_model=List[schemas.Resource])
async def list_resources(
    type: Optional[str] = Query(None),
    tag_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Async: List resources, with optional filtering by type or tag, and pagination.
    """
    return await crud.list_resources(db, type=type, tag_id=tag_id, skip=skip, limit=limit)

@router.put("/{resource_id}", response_model=schemas.Resource)
async def update_resource(resource_id: int, resource: schemas.ResourceCreate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Async: Update a resource by its ID.
    """
    tag_ids = get_tag_ids(resource)
    updates = resource.dict(exclude_unset=True, exclude={"tag_ids"})
    db_resource = await crud.update_resource(db, resource_id, updates, tag_ids=tag_ids)
    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return db_resource

@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(resource_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Async: Delete a resource by its ID.
    """
    db_resource = await crud.delete_resource(db, resource_id)
    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return None 