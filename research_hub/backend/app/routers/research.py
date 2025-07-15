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
