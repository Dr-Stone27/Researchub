"""
utils.py

Utility functions for the Research Resource Hub backend.
Includes email sending stub and ElasticSearch search stub.
All functions are documented for clarity and auditability.
"""
# Utility functions will be defined here 

from fastapi.security import OAuth2PasswordBearer
from app.models import UserActivity, Notification
from sqlalchemy.orm import Session
import json
from app.settings import settings
import redis.asyncio as redis
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.settings import settings




def send_email(
    to: str,
    subject: str,
    body: str,
    attachments=None,  # Keeping signature but not using
    is_html: bool = False,
    **kwargs
) -> bool:
    """
    Send email using SendGrid API (without attachments)
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text or HTML)
        attachments: Ignored (kept for compatibility)
        is_html: True if body is HTML, False for plain text
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Validate configuration
    if not settings.email_api_key:
        print("SendGrid API key missing in configuration")
        return False
        
    if not settings.email_sender:
        print("Email sender address missing in configuration")
        return False

    try:
        # Create Mail object with basic parameters
        message = Mail(
            from_email=settings.email_sender,
            to_emails=to,
            subject=subject
        )
        
        # Set content type based on is_html flag
        if is_html:
            message.add_content(body, "text/html")
        else:
            message.add_content(body, "text/plain")
        
        # Initialize SendGrid client
        sg = SendGridAPIClient(api_key=settings.email_api_key)
        
        # Handle EU data residency if needed
        if getattr(settings, 'sendgrid_eu_residency', False):
            sg.client.set_sendgrid_data_residency("eu")
        
        # Send email
        response = sg.send(message)
        
        # Check for success (2xx status code)
        if 200 <= response.status_code < 300:
            return True
        
        print(f"SendGrid error {response.status_code}: {response.body.decode('utf-8')}")
        return False
    
    except Exception as e:
        print(f"SendGrid exception: {str(e)}")
        return False 

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
        meta_info=json.dumps(meta_info) if meta_info else None
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