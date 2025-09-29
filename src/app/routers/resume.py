"""
resume.py

API endpoints for resume upload and management in the Research Resource Hub backend.
Handles file uploads to Firebase Storage and stores metadata in database.
"""

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from sqlalchemy import select, update
from app import schemas
from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.cloudinary_utils import upload_resume_to_cloudinary, delete_resume
from typing import Dict, Optional
import uuid
import os
from datetime import datetime

router = APIRouter(prefix="/api/resume", tags=["Resume Management"])
oauth2_scheme = HTTPBearer(auto_error=False)

# Allowed file types for resumes
ALLOWED_RESUME_TYPES = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post(
    "/upload",
    summary="Upload user resume",
    response_model=schemas.ResumeUploadResponse,
)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
) -> Dict[str, str]:
    """
    Upload and store user resume to Firebase Storage.
    Supports PDF, DOC, and DOCX formats up to 5MB.
    """

    # Validate file type
    if file.content_type not in ALLOWED_RESUME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_RESUME_TYPES.values())}",
        )

    # Read file content once
    file_content = await file.read()

    # Check file size
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size too large. Maximum size is 5MB.",
        )

    try:

        # Upload to Cloudinary
        upload_result = await upload_resume_to_cloudinary(
            file_content, file.filename, current_user.id
        )

        if not upload_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload resume: {upload_result['error']}",
            )

        # Update user record with resume URL
        await db.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(
                resume_url=upload_result["url"],
                resume_filename=file.filename,
                resume_updated_at=datetime.utcnow(),
            )
        )
        await db.commit()

        return {
            "message": "Resume uploaded successfully",
            "resume_url": upload_result["url"],
            "filename": file.filename,
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload resume: {str(e)}",
        )


@router.get(
    "/download",
    summary="Get resume download URL",
    response_model=list[schemas.ResumeDownloadResponse],
)
async def get_resume_url(
    current_user: User = Depends(get_current_user),
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
) -> Dict[str, Optional[str]]:
    """
    Get the current user's resume download URL.
    """
    return {
        "resume_url": getattr(current_user, "resume_url", None),
        "filename": getattr(current_user, "resume_filename", None),
        "updated_at": getattr(current_user, "resume_updated_at", None),
    }


@router.delete(
    "/delete", summary="Delete user resume", response_model=schemas.ResumeDeleteResponse
)
async def delete_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
) -> Dict[str, str]:
    """
    Delete the current user's resume from Firebase and database.
    """
    if not getattr(current_user, "resume_url", None):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No resume found for this user",
        )

    try:
        # Extract public_id from Cloudinary URL for deletion
        resume_url = current_user.resume_url

        # Extract public_id from Cloudinary URL
        # URL format: https://res.cloudinary.com/cloud_name/raw/upload/v123/folder/filename
        if "cloudinary.com" in resume_url:
            public_id = resume_url.split("/upload/")[1].split("?")[0]
            if public_id.startswith("v"):  # Remove version number
                public_id = "/".join(public_id.split("/")[1:])

            # Delete from Cloudinary
            await delete_resume(public_id)

        # Update user record to remove resume references
        await db.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(resume_url=None, resume_filename=None, resume_updated_at=None)
        )
        await db.commit()

        return {"message": "Resume deleted successfully"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete resume: {str(e)}",
        )


@router.get(
    "/info", summary="Get resume information", response_model=schemas.ResumeInfoResponse
)
async def get_resume_info(
    current_user: User = Depends(get_current_user),
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    """
    Get detailed information about the user's resume.
    """
    return {
        "has_resume": bool(getattr(current_user, "resume_url", None)),
        "filename": getattr(current_user, "resume_filename", None),
        "uploaded_at": getattr(current_user, "resume_updated_at", None),
        "max_file_size": f"{MAX_FILE_SIZE / (1024*1024)}MB",
        "allowed_formats": list(ALLOWED_RESUME_TYPES.values()),
    }
