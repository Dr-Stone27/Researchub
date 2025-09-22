from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import schemas, crud, models
from app.database import get_db
from app.firebase_utils import upload_file_to_firebase
from app.auth import verify_access_token
from app.utils import log_user_activity, parse_tag_ids  # For user activity logging
from sqlalchemy.orm import selectinload
from enum import Enum
from typing import Dict
import uuid

router = APIRouter()

oauth2_scheme = HTTPBearer(auto_error=True)

async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> models.User:
    raw_token = token.credentials
    payload = verify_access_token(raw_token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user_id = int(payload["sub"])

    stmt = select(models.User).where(
        models.User.id == user_id,
        models.User.is_active == True,
        models.User.is_verified == True,
        models.User.account_status == "active"
    )
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=403, detail="User account is not active or verified.")
    return user

@router.post("/submissions", response_model=schemas.ResearchSubmissionResponse)
async def upload_submission(
    title: str = Form(...),
    abstract: str = Form(...),
    supervisor: Optional[str] = Form(None),
    year: int = Form(...),
    tag_ids: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Any:
    filename = f"research/{uuid.uuid4()}_{file.filename}"
    file_url = upload_file_to_firebase(file, filename)

    tag_id_list = parse_tag_ids(tag_ids)

    submission_dict = {
        "title": title,
        "abstract": abstract,
        "supervisor": supervisor,
        "year": year,
        "file_url": file_url,
        "status": "pending",
        "user_id": current_user.id,
    }

    db_submission = await crud.create_submission(db, submission_dict, tag_id_list)

    # Eager load tags here:
    await db.refresh(db_submission, attribute_names=["tags"])

    # Convert to Pydantic schema inside async context to avoid lazy loading outside
    response_data = schemas.ResearchSubmissionResponse.from_orm(db_submission)

    log_user_activity(
        db=db,
        user_id=current_user.id,
        action_type="submit",
        target_type="research",
        target_id=db_submission.id,
        metadata={"title": title},
    )

    return response_data


@router.get("/submissions/{id}", response_model=schemas.ResearchSubmissionResponse)
async def get_submission(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Any:
    submission = await crud.get_submission_by_id(db, id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    log_user_activity(
        db=db,
        user_id=current_user.id,
        action_type="view",
        target_type="research",
        target_id=id,
    )
    return submission

@router.get("/submissions", response_model=List[schemas.ResearchSubmissionResponse])
async def list_submissions(
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await crud.list_submissions(db)


async def get_current_faculty(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if current_user.role not in ["contributor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Faculty access required."
        )
    return current_user

# Review endpoints
@router.get("/reviews/pending", response_model=List[schemas.PendingSubmissionItem])
async def get_pending_submissions(
    reviewer_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_faculty),
) -> Any:
    """
    Get pending submissions for faculty dashboard.
    If reviewer_id is provided, filter by specific reviewer's assigned submissions.
    """
    # Base query for pending submissions
    stmt = select(models.ResearchSubmission).where(
        models.ResearchSubmission.status == "pending"
    ).options(
        selectinload(models.ResearchSubmission.tags),
        selectinload(models.ResearchSubmission.user)
    )
    
    # If reviewer_id is provided, filter submissions assigned to that reviewer
    # (You might want to implement an assignment system later)
    if reviewer_id:
        # For now, we'll return all pending submissions
        # You can implement assignment logic here
        pass
    
    result = await db.execute(stmt)
    submissions = result.scalars().all()
    
    pending_items = []
    for submission in submissions:
        # Convert tags to TagResponse
        tag_responses = [schemas.TagResponse.from_orm(tag) for tag in submission.tags]
        
        pending_items.append(schemas.PendingSubmissionItem(
            submission_id=submission.id,
            title=submission.title,
            abstract=submission.abstract,
            year=submission.year,
            supervisor=submission.supervisor,
            user_name=submission.user.name,
            department=submission.user.department,
            tags=tag_responses,
            created_at=submission.created_at
        ))
    
    return pending_items

@router.get("/reviews/{submission_id}", response_model=schemas.SubmissionWithReviewsResponse)
async def get_submission_with_reviews(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_faculty),
) -> Any:
    """
    Get submission details along with previous reviews.
    """
    # Get submission with eager loading
    stmt = select(models.ResearchSubmission).where(
        models.ResearchSubmission.id == submission_id
    ).options(
        selectinload(models.ResearchSubmission.tags),
        selectinload(models.ResearchSubmission.user),
        selectinload(models.ResearchSubmission.reviews).selectinload(models.Review.reviewer)
    )
    
    result = await db.execute(stmt)
    submission = result.scalars().first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Convert submission to response schema
    submission_response = schemas.ResearchSubmissionResponse.from_orm(submission)
    
    # Convert reviews to response schema
    previous_reviews = []
    for review in submission.reviews:
        previous_reviews.append(schemas.ReviewResponse(
            id=review.id,
            submission_id=review.submission_id,
            reviewer_id=review.reviewer_id,
            reviewer_name=review.reviewer.name,
            action=review.action,
            comments=review.comments,
            created_at=review.created_at
        ))
    
    return schemas.SubmissionWithReviewsResponse(
        submission=submission_response,
        previous_reviews=previous_reviews
    )

@router.post("/reviews/{submission_id}", response_model=schemas.ReviewResponse)
async def create_review(
    submission_id: int,
    review_data: schemas.ReviewBase,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_faculty),
) -> Any:
    """
    Submit a review for a submission (Approve/Reject/Request Revision).
    """
    # Check if submission exists
    stmt = select(models.ResearchSubmission).where(
        models.ResearchSubmission.id == submission_id
    )
    result = await db.execute(stmt)
    submission = result.scalars().first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Create review
    review_dict = {
        "submission_id": submission_id,
        "reviewer_id": current_user.id,
        "action": review_data.action,
        "comments": review_data.comments
    }
    
    db_review = models.Review(**review_dict)
    db.add(db_review)
    
    # Update submission status based on review action
    if review_data.action == schemas.ReviewAction.APPROVE:
        submission.status = "approved"
    elif review_data.action == schemas.ReviewAction.REJECT:
        submission.status = "rejected"
    elif review_data.action == schemas.ReviewAction.REVISION:
        submission.status = "revision_requested"
    
    await db.commit()
    await db.refresh(db_review)
    
    # Log activity
    log_user_activity(
        db=db,
        user_id=current_user.id,
        action_type="review",
        target_type="research",
        target_id=submission_id,
        metadata={"action": review_data.action, "submission_title": submission.title},
    )
    
    # Return review response
    return schemas.ReviewResponse(
        id=db_review.id,
        submission_id=db_review.submission_id,
        reviewer_id=db_review.reviewer_id,
        reviewer_name=current_user.name,
        action=db_review.action,
        comments=db_review.comments,
        created_at=db_review.created_at
    )