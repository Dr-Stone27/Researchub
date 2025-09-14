"""
users.py

API endpoints for user registration and authentication in the Research Resource Hub backend.
All endpoints and helper functions are async for scalability and auditability.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Body, Request, BackgroundTasks
from sqlalchemy import select
from app import schemas, crud, auth, models
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
import secrets

from datetime import datetime, timedelta
from app.utils import check_and_increment_rate_limit, send_email
from app.settings import settings
import re
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler

router = APIRouter()

# In-memory rate limiter (for demonstration; use Redis or similar for production)
RATE_LIMIT = 5  # max attempts
RATE_PERIOD = 600  # seconds (10 minutes)


@router.post("/register", response_model=schemas.UserResponse)
async def register_user(
    user: schemas.UserCreate,
     background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
   
) -> Any:
    if await crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail={"email": "This email is already registered."})
    
    if user.matric_or_faculty_id and await crud.get_user_by_matric_or_faculty_id(db, user.matric_or_faculty_id):
        raise HTTPException(status_code=400, detail={"matric_or_faculty_id": "This Matric Number/Faculty ID is already registered."})

    hashed_password = auth.hash_password(user.password)
    user_dict = user.dict()
    user_dict.pop("password")
    user_dict["password_hash"] = hashed_password
    verification_token = secrets.token_urlsafe(32)
    verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
    user_dict.update({
        "verification_token": verification_token,
        "verification_token_expiry": verification_token_expiry,
        "is_verified": False,
        "account_status": "pending_verification"
    })

    # Create user and commit transaction
    db_user = await crud.create_user(db, user_dict)
    await db.commit()  # ✅ Commit the transaction
    await db.refresh(db_user)  # ✅ Refresh to load database defaults

    verification_link = f"https://researchub-3zyb.onrender.com/verify-email?token={verification_token}"
    email_subject = "Verify your UNILAG Research Hub account"
    email_body = f"""
    Dear {user.name},

    Thank you for registering at the UNILAG Research Hub.
    Please verify your email address by clicking the link below:
    {verification_link}

    This link will expire in 24 hours.

    If you did not register, please ignore this email.
    """
    
    background_tasks.add_task(send_email, user.email, email_subject, email_body)
    
    # Use Pydantic's model_validate for proper serialization
    return schemas.UserResponse.model_validate(db_user)

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app import auth, crud, schemas
from app.database import get_db
from datetime import datetime
from fastapi import Request  
@router.post("/login")
async def login_user(
      request: Request, 
    login_data: schemas.UserLogin,
    db: AsyncSession = Depends(get_db),
   
):
    ip = request.client.host
    allowed = await check_and_increment_rate_limit(ip, RATE_LIMIT, RATE_PERIOD, settings.redis_url)
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
    
    user = await crud.get_user_by_email(db, login_data.email_or_matric)
    if not user and login_data.email_or_matric:
        user = await crud.get_user_by_matric_or_faculty_id(db, login_data.email_or_matric)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not auth.verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not user.is_verified or not user.is_active or user.account_status != "active":
        raise HTTPException(status_code=403, detail="Account not active or not verified.")
    
    if not user.first_login:
        user.first_login = datetime.utcnow()
    user.last_login = datetime.utcnow()
    await db.commit()

    token = auth.create_access_token({"sub": str(user.id), "role": user.role}, token_version=user.token_version)

    return {
        "token": token,
        "user": schemas.UserResponse.model_validate(user),  # ✅ convert model to schema
        "first_login": user.first_login,
        "last_login": user.last_login
    }
@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Async: Verify a user's email using the verification token.
    Handles expired/invalid tokens and already verified accounts with clear responses.
    """
    # Use ORM-style query to get the User object
    result = await db.execute(
        select(models.User).where(models.User.verification_token == token)
    )
    user = result.scalar_one_or_none()  # Get the User instance or None
    
    if not user:
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid or expired verification link."}
        )
    
    if user.is_verified:
        return JSONResponse(
            status_code=200,
            content={"message": "Account already verified. Please log in."}
        )
    
    if not user.verification_token_expiry or user.verification_token_expiry < datetime.utcnow():
        return JSONResponse(
            status_code=400,
            content={"detail": "Verification link has expired. Please request a new one."}
        )
    
    # Update the user attributes
    user.is_verified = True
    user.account_status = "active"
    user.verification_token = None
    user.verification_token_expiry = None
    
    # Add the modified user to the session and commit
    db.add(user)
    await db.commit()
    
    return JSONResponse(
        status_code=200,
        content={"message": "Email verified successfully. You may now log in."}
    )

@router.post("/resend-verification")
async def resend_verification(email: str = Body(..., embed=True), db: AsyncSession = Depends(get_db), background_tasks: BackgroundTasks = None):
    """
    Async: Resend the verification email to a user who is not yet verified.
    Args:
        email (str): The user's email address.
    Returns:
        Success or error message.
    """
    user = await crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.is_verified:
        return {"message": "Account already verified. Please log in."}
    # Generate new token and expiry
    verification_token = secrets.token_urlsafe(32)
    verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
    user.verification_token = verification_token
    user.verification_token_expiry = verification_token_expiry
    await db.commit()
    # Send verification email
    verification_link = f"https://researchub-3zyb.onrender.com/verify-email?token={verification_token}"
    email_subject = "Verify your UNILAG Research Hub account"
    email_body = f"""
    Dear {user.name},

    Please verify your email address by clicking the link below:
    {verification_link}

    This link will expire in 24 hours.

    If you did not request this, please ignore this email.
    """
    background_tasks.add_task(send_email, user.email, email_subject, email_body)
    return {"message": "Verification email resent. Please check your inbox."}

@router.post("/forgot-password")
async def forgot_password(
    email: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    user = await crud.get_user_by_email(db, email)
    if user:
        # Generate 6-digit numeric code
        reset_code = ''.join(secrets.choice('0123456789') for _ in range(6))
        reset_expiry = datetime.utcnow() + timedelta(minutes=10)  # Shorter expiry
        
        # Store in database
        user.password_reset_token = reset_code
        user.password_reset_token_expiry = reset_expiry
        await db.commit()
        
        # Prepare email with code
        email_subject = "UNILAG Research Hub Password Reset Code"
        email_body = f"""
        Dear {user.name},

        Your password reset verification code is:
        {reset_code}

        This code will expire in 10 minutes. If you didn't request this, please ignore this email.

        Regards,
        UNILAG Research Hub Team
        """
        
        background_tasks.add_task(send_email, user.email, email_subject, email_body)
    
    return {"message": "If an account exists with this email, a verification code has been sent."}


@router.post("/reset-password")
async def reset_password(
    token: str = Body(..., embed=True),  # Now holds the 6-digit code
    new_password: str = Body(..., embed=True),
   
    db: AsyncSession = Depends(get_db)
):
    """
    Async: Reset password using a valid 6-digit reset code.
    Validates code, expiry, and password strength.
    """
    # Find user by reset code
    from sqlalchemy import select
    result = await db.execute(
        select(models.User).filter(models.User.password_reset_token == token)
    )
    user = result.scalars().first()
    
    # Validate code and expiry
    if not user or not user.password_reset_token_expiry or user.password_reset_token_expiry < datetime.utcnow():
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid or expired verification code."}
        )
    
    # Password validation (unchanged)
    if new_password:
        return JSONResponse(
            status_code=400,
            content={"detail": {"confirm_password": "Passwords do not match."}}
        )
    if len(new_password) < 8 or \
       not re.search(r"[A-Z]", new_password) or \
       not re.search(r"[a-z]", new_password) or \
       not re.search(r"\d", new_password) or \
       not re.search(r"[^A-Za-z0-9]", new_password):
        return JSONResponse(
            status_code=400,
            content={"detail": {"new_password": "Password must be at least 8 characters long and include uppercase, lowercase, number, and special character."}}
        )
    
    # Update password and clear reset code
    from app.auth import hash_password
    user.password_hash = hash_password(new_password)
    user.password_reset_token = None  # Clear reset code
    user.password_reset_token_expiry = None  # Clear expiry
    user.token_version += 1  # Invalidate existing JWTs
    await db.commit()
    
    return {"message": "Password reset successful. You may now log in with your new password."}
# User-related endpoints will be defined here
