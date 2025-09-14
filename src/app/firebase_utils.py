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




def upload_file_to_firebase(file_obj: UploadFile, filename: str) -> str:
    bucket = get_bucket()
    blob = bucket.blob(filename)
    # file_obj.file is the SpooledTemporaryFile; file_obj.content_type is available
    blob.upload_from_file(file_obj.file, content_type=file_obj.content_type)
    blob.make_public()
    return blob.public_url


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
