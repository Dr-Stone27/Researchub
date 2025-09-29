"""
cloudinary_utils.py

Cloudinary integration for file uploads in the Research Resource Hub backend.
Handles resume uploads and file management using Cloudinary service.
"""

import cloudinary
import cloudinary.uploader
from app.settings import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)


async def upload_resume_to_cloudinary(file_content: bytes, filename: str, user_id: int) -> dict:
    """
    Upload resume file to Cloudinary.

    Args:
        file_content: File content as bytes
        filename: Original filename
        user_id: User ID for folder organization

    Returns:
        dict: Upload result with URL and public_id
    """
    try:
        # Create a unique filename
        file_extension = filename.split(".")[-1]
        public_id = f"resumes/user_{user_id}/resume_{user_id}.{file_extension}"

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file_content,
            public_id=public_id,
            resource_type="raw",  # For non-image files like PDFs
            folder="researchub/resumes",
            overwrite=True,  # Replace existing file
            invalidate=True,  # Clear CDN cache
            tags=["resume", f"user_{user_id}"],
        )

        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "original_filename": filename,
            "file_size": result.get("bytes", 0),
            "format": result.get("format", file_extension),
        }

    except Exception as e:
        logger.error(f"Cloudinary upload failed: {str(e)}")
        return {"success": False, "error": str(e)}


async def delete_resume(public_id: str) -> bool:
    """
    Delete resume file from Cloudinary.

    Args:
        public_id: Cloudinary public ID of the file

    Returns:
        bool: True if deletion successful
    """
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="raw")
        return result.get("result") == "ok"

    except Exception as e:
        logger.error(f"Cloudinary deletion failed: {str(e)}")
        return False


def get_resume_url(public_id: str) -> Optional[str]:
    """
    Get the URL for a resume file.

    Args:
        public_id: Cloudinary public ID

    Returns:
        str: Secure URL to the file
    """
    try:
        url = cloudinary.utils.cloudinary_url(
            public_id, resource_type="raw", secure=True
        )[0]
        return url
    except Exception as e:
        logger.error(f"Failed to generate URL: {str(e)}")
        return None
