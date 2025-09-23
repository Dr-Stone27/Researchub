"""
library.py

API endpoints for browsing, searching, and downloading research submissions in the Research Resource Hub backend.
All endpoints and helper functions are async for scalability and auditability.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app import models, schemas
from typing import List, Optional, Any
from fastapi.responses import RedirectResponse
from app.utils import create_notification

router = APIRouter()

@router.get("/library/{submission_id}", response_model=schemas.ResearchSubmissionResponse)
async def get_submission_detail(
    submission_id: int,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Async: Get detailed information about a single research submission by ID.
    """
    # Query with eager loading for all relationships
    query = select(models.ResearchSubmission).options(
        selectinload(models.ResearchSubmission.user),
        selectinload(models.ResearchSubmission.tags)
    ).filter(models.ResearchSubmission.id == submission_id)
    
    result = await db.execute(query)
    submission = result.scalars().first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Only return approved submissions (or allow admins to see all)
    if submission.status != "approved":
        # In a real implementation, you might want to check user permissions here
        # For now, we'll only return approved submissions to all users
        raise HTTPException(status_code=404, detail="Submission not found or not approved")
    
    return submission


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
    # Base query with eager loading for relationships
    query = select(models.ResearchSubmission).options(
        selectinload(models.ResearchSubmission.user),
        selectinload(models.ResearchSubmission.tags)
    )
    
    # Apply filters
    if department:
        query = query.join(models.User).filter(models.User.department == department)
    if year:
        query = query.filter(models.ResearchSubmission.year == year)
    if supervisor:
        query = query.filter(models.ResearchSubmission.supervisor.ilike(f"%{supervisor}%"))
    if status:
        query = query.filter(models.ResearchSubmission.status == status)
    
    # FIXED: Handle tag_ids safely
    if tag_ids:
        try:
            # Parse comma-separated integers
            tag_id_list = []
            for tid in tag_ids.split(","):
                if tid.strip().isdigit():
                    tag_id_list.append(int(tid))
            
            if tag_id_list:
                query = query.join(models.ResearchSubmission.tags).filter(models.Tag.id.in_(tag_id_list))
        except ValueError:
            # Log error but don't fail the entire request
            logger.warning(f"Invalid tag_ids parameter: {tag_ids}")
    
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
    # Base query with eager loading for relationships
    query = select(models.ResearchSubmission).options(
        selectinload(models.ResearchSubmission.user),
        selectinload(models.ResearchSubmission.tags)
    )
    
    # Full-text search
    search = f"%{q}%"
    query = query.filter(
        (models.ResearchSubmission.title.ilike(search)) |
        (models.ResearchSubmission.abstract.ilike(search)) |
        (models.ResearchSubmission.supervisor.ilike(search))
    )
    
    # Apply filters
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
    
    # Track downloads and notify at milestones
    download_count_result = await db.execute(
        select(models.UserActivity).filter(
            models.UserActivity.action_type == "download",
            models.UserActivity.target_type == "research",
            models.UserActivity.target_id == submission_id
        )
    )
    download_count = len(download_count_result.scalars().all())
    
    # Notify uploader every 10 downloads
    if submission.user_id and download_count > 0 and download_count % 10 == 0:
        await create_notification(
            db, 
            submission.user_id, 
            f"Your research '{submission.title}' has been downloaded {download_count} times!", 
            "download", 
            resource_id=submission_id
        )
    
    return RedirectResponse(url=file_url)