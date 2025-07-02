"""
library.py

API endpoints for browsing, searching, and downloading research submissions in the Research Resource Hub backend.
All endpoints and helper functions are async for scalability and auditability.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app import models, schemas
from typing import List, Optional, Any
from fastapi.responses import RedirectResponse
from app.utils import create_notification

router = APIRouter()

@router.get("/library/browse", response_model=List[schemas.ResearchSubmissionResponse])
async def browse_library(
    department: Optional[str] = None,
    year: Optional[int] = None,
    supervisor: Optional[str] = None,
    status: Optional[str] = "approved",
    tag_ids: Optional[str] = None,  # Comma-separated tag IDs
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Async: Browse research submissions with advanced filters and pagination.
    """
    query = select(models.ResearchSubmission)
    if department:
        query = query.join(models.User).filter(models.User.department == department)
    if year:
        query = query.filter(models.ResearchSubmission.year == year)
    if supervisor:
        query = query.filter(models.ResearchSubmission.supervisor.ilike(f"%{supervisor}%"))
    if status:
        query = query.filter(models.ResearchSubmission.status == status)
    if tag_ids:
        tag_id_list = [int(tid) for tid in tag_ids.split(",")]
        query = query.join(models.ResearchSubmission.tags).filter(models.Tag.id.in_(tag_id_list))
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/library/search", response_model=List[schemas.ResearchSubmissionResponse])
async def search_library(
    q: str,
    department: Optional[str] = None,
    year: Optional[int] = None,
    supervisor: Optional[str] = None,
    status: Optional[str] = "approved",
    tag_ids: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Async: Full-text search for research submissions with filters and pagination.
    """
    query = select(models.ResearchSubmission)
    # Basic full-text search on title, abstract, supervisor
    search = f"%{q}%"
    query = query.filter(
        (models.ResearchSubmission.title.ilike(search)) |
        (models.ResearchSubmission.abstract.ilike(search)) |
        (models.ResearchSubmission.supervisor.ilike(search))
    )
    if department:
        query = query.join(models.User).filter(models.User.department == department)
    if year:
        query = query.filter(models.ResearchSubmission.year == year)
    if supervisor:
        query = query.filter(models.ResearchSubmission.supervisor.ilike(f"%{supervisor}%"))
    if status:
        query = query.filter(models.ResearchSubmission.status == status)
    if tag_ids:
        tag_id_list = [int(tid) for tid in tag_ids.split(",")]
        query = query.join(models.ResearchSubmission.tags).filter(models.Tag.id.in_(tag_id_list))
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/library/{submission_id}/download")
async def download_submission(submission_id: int, db: AsyncSession = Depends(get_db)):
    """
    Async: Download a research submission file by its ID.
    """
    result = await db.execute(select(models.ResearchSubmission).filter(models.ResearchSubmission.id == submission_id))
    submission = result.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    file_url = submission.file_url
    if not file_url:
        raise HTTPException(status_code=404, detail="File not found")
    # Notify uploader if download milestone is reached (e.g., every 10 downloads)
    download_count_result = await db.execute(
        select(models.UserActivity).filter(
            models.UserActivity.action_type == "download",
            models.UserActivity.target_type == "research",
            models.UserActivity.target_id == submission_id
        )
    )
    download_count = len(download_count_result.scalars().all())
    if submission.user_id and download_count > 0 and download_count % 10 == 0:
        await create_notification(db, submission.user_id, f"Your research '{submission.title}' has been downloaded {download_count} times!", "download", resource_id=submission_id)
    return RedirectResponse(url=file_url) 