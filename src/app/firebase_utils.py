"""
firebase_utils.py

Utility functions for Firebase integration. Uses centralized settings from app.settings for any config or secrets.
"""

from fastapi import UploadFile, HTTPException, status
import firebase_admin
from firebase_admin import credentials, storage
import os
import json
from dotenv import load_dotenv
from urllib.parse import urlparse, unquote

load_dotenv()  # Load env variables from .env file (local dev)

# Load Firebase credentials from file path
firebase_cred_path = os.getenv("FIREBASE_CRED_PATH", "firebase_credentials.json")

if firebase_cred_path and os.path.exists(firebase_cred_path):
    try:
        cred = credentials.Certificate(firebase_cred_path)
    except Exception as e:
        print(f"Warning: Could not load Firebase credentials: {e}")
        cred = None
else:
    print(f"Warning: Firebase credentials file not found at: {firebase_cred_path}")
    cred = None

FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "your-bucket-name")

# Initialize Firebase app if not already initialized
if not firebase_admin._apps and cred:
    try:
        firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_STORAGE_BUCKET})
        print("Firebase initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize Firebase: {e}")
elif not cred:
    print("Warning: Firebase not initialized - credentials not available")


def get_bucket():
    return storage.bucket()


def upload_file_to_firebase(file_obj: UploadFile, filename: str) -> str:
    # File type validation
    allowed_types = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "text/plain",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/vnd.ms-excel",  # .xls
    ]

    if file_obj.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_obj.content_type} not allowed. Allowed types: PDF, DOC, DOCX, TXT, Excel",
        )

    # File size validation (10MB limit)
    max_size = 10 * 1024 * 1024  # 10MB in bytes

    # Get file size by seeking to end and back
    file_obj.file.seek(0, 2)  # Seek to end
    file_size = file_obj.file.tell()
    file_obj.file.seek(0)  # Reset to beginning

    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size {file_size} exceeds maximum allowed size of {max_size} bytes",
        )

    # Additional validation: check file extension matches content type
    allowed_extensions = [".pdf", ".doc", ".docx", ".txt", ".xlsx", ".xls"]
    file_extension = os.path.splitext(file_obj.filename)[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension {file_extension} not allowed",
        )

    # Proceed with upload if all validations pass
    bucket = get_bucket()
    blob = bucket.blob(filename)

    try:
        blob.upload_from_file(file_obj.file, content_type=file_obj.content_type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}",
        )

def delete_file_from_firebase(file_url_or_filename: str) -> bool:
    """
    Delete a file from Firebase Storage using either the file URL or filename.
    
    Args:
        file_url_or_filename: Either the full Firebase Storage URL or just the filename/path
        
    Returns:
        bool: True if deletion was successful, False otherwise
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        # Extract filename from URL if a full URL is provided
        if file_url_or_filename.startswith('http'):
            # Parse the URL to extract the filename
            # Firebase Storage URLs have format: https://storage.googleapis.com/bucket-name/filename
            # or https://firebasestorage.googleapis.com/v0/b/bucket-name/o/filename?...
            
            parsed_url = urlparse(file_url_or_filename)
            if 'firebasestorage.googleapis.com' in parsed_url.netloc:
                # Handle Firebase Storage API URL format
                path_parts = parsed_url.path.split('/o/')
                if len(path_parts) > 1:
                    filename = unquote(path_parts[1].split('?')[0])
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid Firebase Storage URL format"
                    )
            elif 'storage.googleapis.com' in parsed_url.netloc:
                # Handle Google Cloud Storage URL format
                path_parts = parsed_url.path.split('/', 2)
                if len(path_parts) > 2:
                    filename = unquote(path_parts[2])
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid storage URL format"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="URL is not a recognized Firebase/Google Cloud Storage URL"
                )
        else:
            # Assume it's already a filename
            filename = file_url_or_filename
        
        bucket = get_bucket()
        blob = bucket.blob(filename)
        
        # Check if file exists before attempting deletion
        if not blob.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {filename} not found in storage"
            )
        
        blob.delete()
        return True
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File deletion failed: {str(e)}"
        )
# from pathlib import Path
# import shutil

# UPLOAD_DIR = Path("uploads")

# def upload_file_to_firebase(file_obj, filename: str) -> str:
#     # Ensure the directory exists
#     UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

#     file_path = UPLOAD_DIR / filename

#     with file_path.open("wb") as buffer:
#         shutil.copyfileobj(file_obj, buffer)

#     # Return URL path relative to your static mount
#     return f"/files/research/{filename}"
