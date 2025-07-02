"""
utils.py

Utility functions for the Research Resource Hub backend.
Includes email sending stub and ElasticSearch search stub.
All functions are documented for clarity and auditability.
"""
# Utility functions will be defined here 

from app.models import UserActivity, Notification
from sqlalchemy.orm import Session
import json
from app.settings import settings
import redis.asyncio as redis

def send_email(to: str, subject: str, body: str, attachments=None):
    """
    Abstract email sending utility.
    Replace this stub with actual integration (e.g., SendGrid, Mailgun).
    Uses settings.email_provider and settings.email_api_key for configuration.
    Args:
        to (str): Recipient email address
        subject (str): Email subject
        body (str): Email body (plain text or HTML)
        attachments (optional): List of file paths or file-like objects
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # TODO: Integrate with actual email service provider using settings.email_provider and settings.email_api_key
    print(f"[Email Stub] To: {to}, Subject: {subject}, Body: {body}, Attachments: {attachments}")
    return True 

def search_resources(query: str):
    """
    Stub for ElasticSearch resource search.
    Replace this with actual ElasticSearch integration.
    Args:
        query (str): The search query string
    Returns:
        list: List of matching resources (empty for now)
    """
    # TODO: Integrate with ElasticSearch
    return [] 

def log_user_activity(
    db: Session,
    user_id: int,
    action_type: str,
    target_type: str = None,
    target_id: int = None,
    metadata: dict = None
):
    """
    Log a user activity event to the UserActivity table.
    Args:
        db (Session): SQLAlchemy database session
        user_id (int): ID of the user performing the action
        action_type (str): Type of action (e.g., 'view', 'download', 'save', 'submit')
        target_type (str, optional): Type of the target entity (e.g., 'research', 'topic')
        target_id (int, optional): ID of the target entity
        metadata (dict, optional): Additional metadata for extensibility (will be stored as JSON string)
    Returns:
        UserActivity: The created UserActivity record
    """
    activity = UserActivity(
        user_id=user_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        metadata=json.dumps(metadata) if metadata else None
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity 

def create_notification(db: Session, user_id: int, message: str, type: str, resource_id: int = None):
    """
    Create a notification for a user.
    Args:
        db (Session): SQLAlchemy database session
        user_id (int): ID of the user to notify
        message (str): Notification message
        type (str): Notification type (e.g., 'comment', 'approval', 'milestone', 'download')
        resource_id (int, optional): Related resource or research ID
    Returns:
        Notification: The created Notification record
    """
    notification = Notification(
        user_id=user_id,
        message=message,
        type=type,
        resource_id=resource_id
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification 

# Async Redis-based rate limiter utility
def get_redis_client():
    return redis.from_url(settings.redis_url, decode_responses=True)

async def check_and_increment_rate_limit(ip: str, limit: int, period: int, redis_url: str) -> bool:
    """
    Returns True if the request is allowed, False if rate limited.
    Increments the count for the given IP in Redis, with expiry.
    """
    r = redis.from_url(redis_url, decode_responses=True)
    key = f"login_attempts:{ip}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, period)
    if count > limit:
        return False
    return True 