from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import distinct

from .. import schemas
from .. import models
from app.auth import verify_access_token
from app.database import AsyncSessionLocal

router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"]
)
 
oauth2_scheme = HTTPBearer(auto_error=True)

# Dependency: async DB session
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as db:
        yield db

# Dependency: get current user from JWT token
async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> models.User:
    # HTTPBearer ensures token is provided
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

# List notifications for a user
@router.get("/", response_model=List[schemas.Notification])
async def list_notifications(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: models.User = Depends(get_current_user)
) -> List[models.Notification]:
    stmt = (
        select(models.Notification)
        .where(models.Notification.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

# Create a notification
@router.post("/", response_model=schemas.Notification, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification_in: schemas.NotificationCreate,
    db: AsyncSession = Depends(get_db),
    _: models.User = Depends(get_current_user)
) -> models.Notification:
    new_notif = models.Notification(**notification_in.dict())
    db.add(new_notif)
    await db.commit()
    await db.refresh(new_notif)
    return new_notif

# Mark notification as read/unread
@router.patch("/{notification_id}/read", response_model=schemas.Notification)
async def mark_as_read(
    notification_id: int,
    is_read: bool,
    db: AsyncSession = Depends(get_db),
    _: models.User = Depends(get_current_user)
) -> models.Notification:
    stmt = select(models.Notification).where(models.Notification.id == notification_id)
    result = await db.execute(stmt)
    notif = result.scalars().first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = is_read
    await db.commit()
    await db.refresh(notif)
    return notif

# Delete a notification
@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    _: models.User = Depends(get_current_user)
) -> None:
    stmt = select(models.Notification).where(models.Notification.id == notification_id)
    result = await db.execute(stmt)
    notif = result.scalars().first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(notif)
    await db.commit()
    return None
