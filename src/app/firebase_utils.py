"""
firebase_utils.py

Utility functions for Firebase integration. Uses centralized settings from app.settings for any config or secrets.
"""

from fastapi import UploadFile
import firebase_admin
from firebase_admin import credentials, storage
import os
import json
from dotenv import load_dotenv

load_dotenv()  # Load env variables from .env file (local dev)

# Instead of file path, load JSON string from env var

firebase_creds_json = os.getenv("FIREBASE_CRED_PATH")

if firebase_creds_json:
    firebase_creds_dict = json.loads(firebase_creds_json)
    cred = credentials.Certificate(firebase_creds_dict)
else:
    # fallback: load from local file (for local dev)
    FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "firebase_credentials.json")
    cred = credentials.Certificate(FIREBASE_CRED_PATH)

FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "your-bucket-name")

# Initialize Firebase app if not already initialized
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'storageBucket': FIREBASE_STORAGE_BUCKET
    })


if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred, {
        'storageBucket': FIREBASE_STORAGE_BUCKET
    })
 
def get_bucket():
    return storage.bucket()




from fastapi import HTTPException, status
import os

def upload_file_to_firebase(file_obj: UploadFile, filename: str) -> str:
    # File type validation
    allowed_types = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'text/plain',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.ms-excel'  # .xls
    ]
    
    if file_obj.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_obj.content_type} not allowed. Allowed types: PDF, DOC, DOCX, TXT, Excel"
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
            detail=f"File size {file_size} exceeds maximum allowed size of {max_size} bytes"
        )
    
    # Additional validation: check file extension matches content type
    allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.xlsx', '.xls']
    file_extension = os.path.splitext(file_obj.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension {file_extension} not allowed"
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
            detail=f"File upload failed: {str(e)}"
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
