from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import schemas
from .. import models, crud
from app.auth import verify_access_token
from app.database import AsyncSessionLocal

router = APIRouter(
    prefix="/resources",
    tags=["Resources"]
)

oauth2_scheme = HTTPBearer(auto_error=True)

# Dependency: async DB session
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as db:
        yield db

# Dependency: get current user via HTTPBearer
async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
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

# Helper to extract tag IDs
def get_tag_ids(resource: schemas.ResourceCreate):
    return getattr(resource, 'tag_ids', None)

@router.post("/", response_model=schemas.Resource, status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource: schemas.ResourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)  # Changed to get user
) -> models.Resource:
    tag_ids = get_tag_ids(resource)
    resource_data = resource.dict(exclude={"tag_ids"})
    # Add current user's ID
    resource_data["created_by"] = current_user.id
    return await crud.create_resource(db, resource_data, tag_ids=tag_ids)

@router.get("/{resource_id}", response_model=schemas.Resource)
async def get_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db)
) -> models.Resource:
    db_resource = await crud.get_resource_by_id(db, resource_id)
    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return db_resource

@router.get("/", response_model=List[schemas.Resource])
async def list_resources(
    type: Optional[str] = None,
    tag_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
) -> List[models.Resource]:
    return await crud.list_resources(db, type=type, tag_id=tag_id, skip=skip, limit=limit)

@router.put("/{resource_id}", response_model=schemas.Resource)
async def update_resource(
    resource_id: int,
    resource: schemas.ResourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)  # Changed to get user
) -> models.Resource:
    tag_ids = get_tag_ids(resource)
    updates = resource.dict(exclude_unset=True, exclude={"tag_ids"})
    # Prevent changing ownership
    if "created_by" in updates:
        del updates["created_by"]
    db_resource = await crud.update_resource(db, resource_id, updates, tag_ids=tag_ids)
    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return db_resource

@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)  # Changed to get user
) -> None:
    success = await crud.delete_resource(db, resource_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resource not found")
    return None

