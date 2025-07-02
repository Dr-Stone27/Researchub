from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from . import models
from .database import get_db
from app.settings import settings

"""
Authentication logic using centralized settings for secrets and config.
All dependencies are async for scalability and auditability.
"""

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# JWT utilities
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, token_version: int = 0):
    to_encode = data.copy()
    to_encode["token_version"] = token_version
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(Authorization: str = Header(...), db: AsyncSession = Depends(get_db)):
    """
    Async: Extract and validate the current user from the JWT token in the Authorization header.
    Raises HTTPException if token is missing, invalid, or user not found.
    Returns the User object if valid.
    Rejects if token_version in JWT does not match user's current token_version (token revocation).
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
    # Token version check for revocation
    if payload.get("token_version") != user.token_version:
        raise HTTPException(status_code=401, detail="Token has been revoked.")
    return user

def require_role(allowed_roles: List[str]):
    """
    Dependency factory to enforce role-based access control on endpoints.
    Usage: Depends(require_role(["faculty", "admin"]))
    """
    async def role_checker(user = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action.")
        return user
    return role_checker 