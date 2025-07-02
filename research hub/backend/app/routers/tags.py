"""
tags.py

API endpoints for managing tags in the Research Resource Hub backend.
All endpoints and helper functions are async for scalability and auditability.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Header
from app import schemas, crud, models
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from typing import Any, List, Optional
from app.auth import verify_access_token
from app.utils import create_notification

router = APIRouter()

async def is_admin():
    """Stub for admin check. In production, check user role from JWT."""
    return True

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

@router.get("/tags", response_model=List[schemas.TagResponse])
async def list_tags(
    category: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Async: List tags, with optional filtering by category, type, or status.
    """
    return await crud.list_tags(db, category, type, status)

@router.post("/tags", response_model=schemas.TagResponse)
async def create_tag(tag: schemas.TagCreate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)) -> Any:
    """
    Async: Create a new tag.
    """
    if await crud.get_tag_by_name(db, tag.name):
        raise HTTPException(status_code=400, detail="Tag already exists")
    tag_dict = tag.dict()
    # In production, set created_by from current user
    tag_dict["created_by"] = None
    db_tag = await crud.create_tag(db, tag_dict)
    return db_tag

@router.patch("/tags/{id}/approve", response_model=schemas.TagResponse)
async def approve_tag(id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)) -> Any:
    """
    Async: Approve a pending tag (admin only).
    """
    if not await is_admin():
        raise HTTPException(status_code=403, detail="Not authorized")
    tag = await crud.approve_tag(db, id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    # Notify tag creator if available
    if tag.created_by:
        await create_notification(db, tag.created_by, f"Your tag '{tag.name}' was approved.", "approval")
    return tag

@router.patch("/tags/{id}/reject", response_model=schemas.TagResponse)
async def reject_tag(id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)) -> Any:
    """
    Async: Reject a pending tag (admin only).
    """
    if not await is_admin():
        raise HTTPException(status_code=403, detail="Not authorized")
    tag = await crud.reject_tag(db, id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag 