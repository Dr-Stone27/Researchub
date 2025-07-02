"""
research.py

API endpoints for managing research submissions in the Research Resource Hub backend.
All endpoints and helper functions are async for scalability and auditability.
"""
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form, Header
from app import schemas, crud, models
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from typing import Any, List, Optional
from app.firebase_utils import upload_file_to_firebase
import uuid
from app.auth import verify_access_token
from app.utils import log_user_activity  # For user activity logging

router = APIRouter()

async def get_current_user(Authorization: str = Header(...), db: AsyncSession = Depends(get_db)):
    """
    Async: Extract and validate the current user from the JWT token in the Authorization header.
    Raises HTTPException if token is missing, invalid, or user not found.
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
    return user

@router.post("/submissions", response_model=schemas.ResearchSubmissionResponse)
async def upload_submission(
    title: str = Form(...),
    abstract: str = Form(...),
    supervisor: str = Form(None),
    year: int = Form(...),
    tag_ids: Optional[str] = Form(None),  # Comma-separated list of tag IDs
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> Any:
    """
    Async: Upload a new research submission (PDF + metadata + tags).
    """
    # Upload file to Firebase (assume this is a sync call for now)
    filename = f"research/{uuid.uuid4()}_{file.filename}"
    file_url = upload_file_to_firebase(file.file, filename)
    # Parse tag_ids
    tag_id_list = [int(tid) for tid in tag_ids.split(",")] if tag_ids else None
    # Create submission in DB
    submission_dict = {
        "title": title,
        "abstract": abstract,
        "supervisor": supervisor,
        "year": year,
        "file_url": file_url,
        "status": "pending",
        "user_id": current_user.id
    }
    db_submission = await crud.create_submission(db, submission_dict, tag_id_list)
    # Log user activity for submission
    await log_user_activity(
        db=db,
        user_id=current_user.id,
        action_type="submit",
        target_type="research",
        target_id=db_submission.id,
        metadata={"title": title}
    )
    return db_submission

@router.get("/submissions/{id}", response_model=schemas.ResearchSubmissionResponse)
async def get_submission(id: int, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(get_current_user)) -> Any:
    submission = await crud.get_submission_by_id(db, id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    # Log user activity for viewing a submission
    await log_user_activity(
        db=db,
        user_id=current_user.id,
        action_type="view",
        target_type="research",
        target_id=id
    )
    return submission

@router.get("/submissions", response_model=List[schemas.ResearchSubmissionResponse])
async def list_submissions(db: AsyncSession = Depends(get_db)) -> Any:
    return await crud.list_submissions(db)

# Research upload, browse, and search endpoints will be defined here 