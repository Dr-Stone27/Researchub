"""
firebase_utils.py

Utility functions for Firebase integration. Uses centralized settings from app.settings for any config or secrets.
"""
import firebase_admin
from firebase_admin import credentials, storage
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

def upload_file_to_firebase(file_obj, filename: str) -> str:
    bucket = get_bucket()
    blob = bucket.blob(filename)
    blob.upload_from_file(file_obj, content_type=file_obj.content_type)
    blob.make_public()
    return blob.public_url 