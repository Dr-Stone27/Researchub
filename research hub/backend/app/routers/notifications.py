"""
notifications.py

API endpoints for managing user notifications in the Research Resource Hub backend.
Includes endpoints for creating, listing, marking as read/unread, and deleting notifications.
All endpoints and helper functions are documented for clarity and auditability.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, database
from app.auth import verify_access_token, get_current_user
from app.database import get_db

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)

# Dependency to get DB session
def get_db():
    """Dependency to provide a database session to endpoints."""
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(Authorization: str = Header(...), db: Session = Depends(get_db)):
    """
    Extract and validate the current user from the JWT token in the Authorization header.
    Raises HTTPException if token is missing, invalid, or user not found.
    """
    if not Authorization or not Authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    token = Authorization.split(" ", 1)[1]
    payload = verify_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user_id = int(payload["sub"])
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_active or not user.is_verified or user.account_status != "active":
        raise HTTPException(status_code=403, detail="User account is not active or verified.")
    return user

# List notifications for a user (with pagination)
@router.get("/", response_model=List[schemas.Notification])
def list_notifications(user_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """
    List notifications for a user, with pagination.
    Args:
        user_id (int): The ID of the user whose notifications to list.
        skip (int): Number of records to skip (pagination).
        limit (int): Maximum number of records to return.
    Returns:
        List of Notification objects.
    """
    return db.query(models.Notification).filter(models.Notification.user_id == user_id).offset(skip).limit(limit).all()

# Create a notification
@router.post("/", response_model=schemas.Notification)
def create_notification(notification: schemas.NotificationCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Create a new notification for a user.
    Args:
        notification (NotificationCreate): Notification data.
    Returns:
        The created Notification object.
    """
    db_notification = models.Notification(**notification.dict())
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

# Mark notification as read/unread
@router.patch("/{notification_id}/read", response_model=schemas.Notification)
def mark_as_read(notification_id: int, is_read: bool, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Mark a notification as read or unread.
    Args:
        notification_id (int): ID of the notification to update.
        is_read (bool): True to mark as read, False to mark as unread.
    Returns:
        The updated Notification object.
    """
    notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = is_read
    db.commit()
    db.refresh(notification)
    return notification

# Delete a notification
@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(notification_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Delete a notification by its ID.
    Args:
        notification_id (int): ID of the notification to delete.
    Returns:
        None (204 No Content)
    """
    notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(notification)
    db.commit()
    return None 