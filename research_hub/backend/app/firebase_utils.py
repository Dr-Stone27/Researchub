"""
firebase_utils.py

Utility functions for Firebase integration. Uses centralized settings from app.settings for any config or secrets.
"""
import firebase_admin
from firebase_admin import credentials, storage
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
from starlette.datastructures import UploadFile
import os

FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "firebase_credentials.json")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "your-bucket-name")

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
