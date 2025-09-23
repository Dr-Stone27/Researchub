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


# Enhanced bulk update endpoint with individual validation
@router.patch("/bulk-read", response_model=schemas.NotificationBulkUpdateResponse)
async def bulk_mark_as_read_enhanced(
    bulk_update: schemas.NotificationBulkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> schemas.NotificationBulkUpdateResponse:
    """
    Bulk mark multiple notifications as read or unread with enhanced validation.
    """
    if not bulk_update.notification_ids:
        return schemas.NotificationBulkUpdateResponse(
            updated_count=0,
            failed_ids=[]
        )
    
    # Remove duplicates
    unique_ids = list(set(bulk_update.notification_ids))
    
    try:
        # Verify notifications exist and belong to the current user
        stmt = select(models.Notification).where(
            models.Notification.id.in_(unique_ids)
        )
        result = await db.execute(stmt)
        notifications = result.scalars().all()
        
        # Separate valid and invalid notifications
        valid_notifications = []
        failed_ids = []
        
        notification_dict = {notif.id: notif for notif in notifications}
        
        for nid in unique_ids:
            notification = notification_dict.get(nid)
            if notification and notification.user_id == current_user.id:
                valid_notifications.append(notification)
            else:
                failed_ids.append(nid)
        
        # Update valid notifications
        for notification in valid_notifications:
            notification.is_read = bulk_update.is_read
        
        await db.commit()
        
        return schemas.NotificationBulkUpdateResponse(
            updated_count=len(valid_notifications),
            failed_ids=failed_ids
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update notifications: {str(e)}"
        )