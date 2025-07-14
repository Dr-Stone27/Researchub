"""
crud.py

Async business logic and database operations for the Research Resource Hub backend.
Defines CRUD functions for users, research submissions, tags, notifications, and resources.
All functions are async and use AsyncSession for auditability and scalability.
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models

# User CRUD

async def get_user_by_email(db: AsyncSession, email: str):
    """Asynchronously retrieve a user by email address."""
    result = await db.execute(select(models.User).filter(models.User.email == email))
    return result.scalars().first()

async def get_user_by_matric_or_faculty_id(db: AsyncSession, matric_or_faculty_id: str):
    """Asynchronously retrieve a user by matric or faculty ID."""
    result = await db.execute(select(models.User).filter(models.User.matric_or_faculty_id == matric_or_faculty_id))
    return result.scalars().first()

# User CRUD

async def create_user(db: AsyncSession, user: dict):
    """Asynchronously create a new user in the database."""
    # Extract valid User model fields
    valid_fields = [column.name for column in models.User.__table__.columns]
    user_data = {key: value for key, value in user.items() if key in valid_fields}
    
    db_user = models.User(**user_data)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
# Research Submission CRUD

async def create_submission(db: AsyncSession, submission: dict, tag_ids=None):
    """Asynchronously create a new research submission, optionally linking tags."""
    db_submission = models.ResearchSubmission(**submission)
    if tag_ids:
        result = await db.execute(select(models.Tag).filter(models.Tag.id.in_(tag_ids)))
        db_submission.tags = result.scalars().all()
    db.add(db_submission)
    await db.commit()
    await db.refresh(db_submission)
    return db_submission

async def get_submission_by_id(db: AsyncSession, submission_id: int):
    """Asynchronously retrieve a research submission by its ID."""
    result = await db.execute(select(models.ResearchSubmission).filter(models.ResearchSubmission.id == submission_id))
    return result.scalars().first()

async def list_submissions(db: AsyncSession):
    """Asynchronously list all research submissions."""
    result = await db.execute(select(models.ResearchSubmission))
    return result.scalars().all()

# Tag CRUD

async def create_tag(db: AsyncSession, tag: dict):
    """Asynchronously create a new tag in the database."""
    db_tag = models.Tag(**tag)
    db.add(db_tag)
    await db.commit()
    await db.refresh(db_tag)
    return db_tag

async def get_tag_by_name(db: AsyncSession, name: str):
    """Asynchronously retrieve a tag by its name."""
    result = await db.execute(select(models.Tag).filter(models.Tag.name == name))
    return result.scalars().first()

async def get_tag_by_id(db: AsyncSession, tag_id: int):
    """Asynchronously retrieve a tag by its ID."""
    result = await db.execute(select(models.Tag).filter(models.Tag.id == tag_id))
    return result.scalars().first()

async def list_tags(db: AsyncSession, category=None, type=None, status=None):
    """Asynchronously list tags, optionally filtering by category, type, or status."""
    query = select(models.Tag)
    if category:
        query = query.filter(models.Tag.category == category)
    if type:
        query = query.filter(models.Tag.type == type)
    if status:
        query = query.filter(models.Tag.status == status)
    result = await db.execute(query)
    return result.scalars().all()

async def approve_tag(db: AsyncSession, tag_id: int):
    """Asynchronously approve a tag by setting its status to 'approved'."""
    tag = await get_tag_by_id(db, tag_id)
    if tag:
        tag.status = "approved"
        await db.commit()
        await db.refresh(tag)
    return tag

async def reject_tag(db: AsyncSession, tag_id: int):
    """Asynchronously reject a tag by setting its status to 'rejected'."""
    tag = await get_tag_by_id(db, tag_id)
    if tag:
        tag.status = "rejected"
        await db.commit()
        await db.refresh(tag)
    return tag

# Resource CRUD
from sqlalchemy.orm import selectinload

async def create_resource(db: AsyncSession, resource: dict, tag_ids=None):
    """Create resource with eager loading of tags"""
    user = await db.get(models.User, resource["created_by"])
    if not user:
        raise HTTPException(
            status_code=400,
            detail=f"User {resource['created_by']} does not exist"
        )
    
    db_resource = models.Resource(**resource)
    if tag_ids:
        result = await db.execute(
            select(models.Tag).filter(models.Tag.id.in_(tag_ids))
        )
        db_resource.tags = result.scalars().all()
    db.add(db_resource)
    await db.commit()
    
    # Refresh and eager load tags
    await db.refresh(db_resource, attribute_names=["tags"])
    return db_resource
from sqlalchemy.orm import selectinload

async def get_resource_by_id(db: AsyncSession, resource_id: int):
    """Retrieve resource with eager loading of tags and user"""
    result = await db.execute(
        select(models.Resource)
        .options(
            selectinload(models.Resource.tags),
            selectinload(models.Resource.user)  # eagerly load user here too
        )
        .filter(models.Resource.id == resource_id)
    )
    return result.scalars().first()

async def list_resources(db: AsyncSession, type: str = None, tag_id: int = None, skip: int = 0, limit: int = 20):
    query = select(models.Resource).options(
        selectinload(models.Resource.tags),
        selectinload(models.Resource.user)  # eagerly load the user relationship
    )
    if type:
        query = query.filter(models.Resource.type == type)
    if tag_id:
        query = query.join(models.Resource.tags).filter(models.Tag.id == tag_id)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

async def update_resource(db: AsyncSession, resource_id: int, updates: dict, tag_ids=None):
    """Update resource with eager loading of tags"""
    if "created_by" in updates:
        del updates["created_by"]
        
    # Get resource with tags loaded
    result = await db.execute(
        select(models.Resource)
        .options(selectinload(models.Resource.tags))
        .filter(models.Resource.id == resource_id)
    )
    resource = result.scalars().first()
    
    if not resource:
        return None
        
    for key, value in updates.items():
        setattr(resource, key, value)
        
    if tag_ids is not None:
        result = await db.execute(
            select(models.Tag).filter(models.Tag.id.in_(tag_ids))
        )
        resource.tags = result.scalars().all()
        
    await db.commit()
    await db.refresh(resource, attribute_names=["tags"])
    return resource

async def delete_resource(db: AsyncSession, resource_id: int):
    """Asynchronously delete a resource by its ID."""
    resource = await get_resource_by_id(db, resource_id)
    if not resource:
        return None
    await db.delete(resource)
    await db.commit()
    return resource