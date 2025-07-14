from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import schemas, crud, models
from app.database import get_db
from app.auth import verify_access_token
from app.utils import create_notification

router = APIRouter()

oauth2_scheme = HTTPBearer(auto_error=True)

async def is_admin() -> bool:
    # Stub for admin check; replace with real role check from user object in prod
    return True

async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> models.User:
    raw_token = token.credentials
    payload = verify_access_token(raw_token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user_id = int(payload["sub"])
    stmt = select(models.User).where(
        models.User.id == user_id,
        models.User.is_active == True,
        models.User.is_verified == True,
        models.User.account_status == "active"
    )
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=403, detail="User account is not active or verified.")
    return user

@router.get("/tags", response_model=List[schemas.TagResponse])
async def list_tags(
    category: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Any:
    return await crud.list_tags(db, category, type, status)

@router.post("/tags", response_model=schemas.TagResponse)
async def create_tag(
    tag: schemas.TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> Any:
    if await crud.get_tag_by_name(db, tag.name):
        raise HTTPException(status_code=400, detail="Tag already exists")
    tag_dict = tag.dict()
    tag_dict["created_by"] = current_user.id  # set creator properly
    db_tag = await crud.create_tag(db, tag_dict)
    return db_tag

@router.patch("/tags/{id}/approve", response_model=schemas.TagResponse)
async def approve_tag(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> Any:
    if not await is_admin():
        raise HTTPException(status_code=403, detail="Not authorized")
    tag = await crud.approve_tag(db, id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if tag.created_by:
        create_notification(db, tag.created_by, f"Your tag '{tag.name}' was approved.", "approval")
    return tag

@router.patch("/tags/{id}/reject", response_model=schemas.TagResponse)
async def reject_tag(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> Any:
    if not await is_admin():
        raise HTTPException(status_code=403, detail="Not authorized")
    tag = await crud.reject_tag(db, id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if tag.created_by:
        create_notification(db, tag.created_by, f"Your tag '{tag.name}' was rejected.", "rejection")
    return tag
