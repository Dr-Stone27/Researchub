"""
schemas.py

Pydantic schemas for request/response validation in the Research Resource Hub backend.
Defines schemas for User, Tag, ResearchSubmission, Notification, Resource, etc.
All fields and relationships are documented for clarity and auditability.
"""
from pydantic import BaseModel, EmailStr, validator, model_validator, constr, Field,field_validator
from typing import Optional, List
from enum import Enum
import re
from datetime import datetime  # Add datetime import

# Department Enum for validation
class DepartmentEnum(str, Enum):
    civil = "Civil Engineering"
    mechanical = "Mechanical Engineering"
    electrical = "Electrical/Electronics Engineering"
    chemical = "Chemical Engineering"
    computer = "Computer Engineering"
    metallurgical = "Metallurgical and Materials Engineering"
    petroleum = "Petroleum and Gas Engineering"
    surveying = "Surveying and Geoinformatics"
    systems = "Systems Engineering"
    biomedical = "Biomedical Engineering"

class UserBase(BaseModel):
    """Base schema for user creation and response."""
    name: str = Field(..., min_length=1)
    email: EmailStr = Field(...)
    matric_or_faculty_id: Optional[str] = Field(None, pattern=r"^\d{9}$")
    department: Optional[DepartmentEnum] = None

class UserCreate(UserBase):
    """Schema for user registration (includes password and confirm_password)."""
    password: str = Field(...)
    confirm_password: str = Field(...)

    @field_validator("password")
    def password_strength(cls, v):
        import re
        if (
            len(v) < 8 or
            not re.search(r"[A-Z]", v) or
            not re.search(r"[a-z]", v) or
            not re.search(r"\d", v) or
            not re.search(r"[^A-Za-z0-9]", v)
        ):
            raise ValueError(
                "Password must be at least 8 characters long and include uppercase, lowercase, number, and special character."
            )
        return v

    @model_validator(mode='after')
    def passwords_match(cls, values):
        pw, cpw = values.password, values.confirm_password
        if pw != cpw:
            raise ValueError("Passwords do not match.")
        return values

class UserLogin(BaseModel):
    """Schema for user login (by email or matric/faculty ID)."""
    email_or_matric: str = Field(..., min_length=1)
    password: str = Field(...)

class UserResponse(UserBase):
    """Schema for user response (includes id, status, role, onboarding, timestamps)."""
    id: int
    is_active: bool
    is_verified: bool
    role: str
    is_first_time: bool
    created_at: datetime  # Changed to datetime
    updated_at: datetime  # Changed to datetime

    # class Config:
    #     orm_mode = True 

    model_config = {
        "from_attributes": True  # THIS enables ORM compatibility in Pydantic v2
    }    

# Tag Schemas
class TagBase(BaseModel):
    """Base schema for tags."""
    name: str
    category: str

class TagCreate(TagBase):
    """Schema for tag creation (optional type and status)."""
    type: Optional[str] = "suggested"
    status: Optional[str] = "pending"

class TagResponse(TagBase):
    """Schema for tag response (includes id, type, status, creator, timestamps)."""
    id: int
    type: str
    status: str
    created_by: Optional[int]
    created_at: datetime  # Changed to datetime
    updated_at: datetime  # Changed to datetime

    class Config:
        orm_mode = True
        from_attributes = True

# Research Submission Schemas
class ResearchSubmissionBase(BaseModel):
    """Base schema for research submissions."""
    title: str
    abstract: str
    supervisor: Optional[str] = None
    year: int

class ResearchSubmissionCreate(ResearchSubmissionBase):
    """Schema for creating a research submission (with optional tag IDs)."""
    tag_ids: Optional[List[int]] = None

class ResearchSubmissionResponse(ResearchSubmissionBase):
    """Schema for research submission response (includes file, status, user, tags, timestamps)."""
    id: int
    file_url: str
    status: str
    user_id: int
    created_at: datetime  # Changed to datetime
    updated_at: datetime  # Changed to datetime
    user: Optional[UserResponse]
    tags: Optional[List[TagResponse]]

    class Config:
        from_attributes = True
        orm_mode = True 

# Notification Schemas
class NotificationBase(BaseModel):
    """Base schema for notifications."""
    user_id: int
    type: str
    message: str
    resource_id: Optional[int] = None

class NotificationCreate(NotificationBase):
    """Schema for creating a notification."""
    pass

class Notification(NotificationBase):
    """Schema for notification response (includes id, read status, timestamps)."""
    id: int
    is_read: bool
    created_at: datetime  # Changed to datetime
    updated_at: datetime  # Changed to datetime

    class Config:
        orm_mode = True

# Resource Schemas
class ResourceBase(BaseModel):
    """Base schema for resources (guides, templates, etc.)."""
    title: str
    description: str
    type: str
    content_url: str
    created_by: int
    tag_ids: Optional[List[int]] = None

class ResourceCreate(ResourceBase):
    """Schema for creating a resource."""
    pass

class Resource(ResourceBase):
    """Schema for resource response (includes id, tags, user, timestamps)."""
    id: int
    created_at: datetime  # Changed to datetime
    updated_at: datetime  # Changed to datetime
    tags: Optional[List[TagResponse]]
    user: Optional[UserResponse]

    class Config:
        orm_mode = True 

# Draft Schemas
class DraftBase(BaseModel):
    """Base schema for drafts."""
    status: str = "draft"
    research_submission_id: Optional[int] = None

class DraftCreate(DraftBase):
    """Schema for creating a draft."""
    pass

class DraftResponse(DraftBase):
    """Schema for draft response (includes id, user, timestamps)."""
    id: int
    user_id: int
    last_edited: datetime  # Changed to datetime
    created_at: datetime  # Changed to datetime

    class Config:
        orm_mode = True

# UserActivity Schemas
class UserActivityBase(BaseModel):
    """Base schema for user activity logging."""
    action_type: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    meta_info: Optional[str] = None

class UserActivityCreate(UserActivityBase):
    """Schema for creating a user activity log."""
    pass

class UserActivityResponse(UserActivityBase):
    """Schema for user activity response (includes id, user, timestamp)."""
    id: int
    user_id: int
    timestamp: datetime  # Changed to datetime

    class Config:
        orm_mode = True

# Milestone Schemas
class MilestoneBase(BaseModel):
    """Base schema for milestones."""
    name: str
    description: str
    criteria: str
    badge_url: Optional[str] = None

class MilestoneCreate(MilestoneBase):
    """Schema for creating a milestone."""
    pass

class MilestoneResponse(MilestoneBase):
    """Schema for milestone response (includes id, created_at)."""
    id: int
    created_at: datetime  # Changed to datetime

    class Config:
        orm_mode = True

# UserMilestone Schemas
class UserMilestoneBase(BaseModel):
    """Base schema for user milestone progress."""
    milestone_id: int

class UserMilestoneCreate(UserMilestoneBase):
    """Schema for creating a user milestone record."""
    pass

class UserMilestoneResponse(UserMilestoneBase):
    """Schema for user milestone response (includes id, user, achieved_at, milestone details)."""
    id: int
    user_id: int
    achieved_at: datetime  # Changed to datetime
    milestone: Optional[MilestoneResponse]

    class Config:
        orm_mode = True

class DashboardFeedItem(BaseModel):
    id: int
    title: str
    authors: List[str]
    department: Optional[str]
    tags: List[str]
    is_featured: bool
    created_at: Optional[datetime]
    summary: str


class DashboardUserStats(BaseModel):
    topics_explored: int
    papers_read: int
    papers_uploaded: int
    total_downloads: int
    profile_views: int

class DashboardUserMilestone(BaseModel):
    milestone_id: int
    name: str
    description: str
    badge_url: Optional[str]
    achieved: bool
    progress: int
    target: int
    achieved_at: Optional[datetime]


class DashboardUserDraftPending(BaseModel):
    id: int
    title: str
    status: str
    last_edited: Optional[datetime]
    is_draft: bool

class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REVISION = "revision"


class ReviewBase(BaseModel):
    comments: str
    action: ReviewAction

class ReviewCreate(ReviewBase):
    submission_id: int
    reviewer_id: int

class ReviewResponse(ReviewBase):
    id: int
    submission_id: int
    reviewer_id: int
    reviewer_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class SubmissionWithReviewsResponse(BaseModel):
    submission: ResearchSubmissionResponse
    previous_reviews: List[ReviewResponse]
    
    class Config:
        from_attributes = True

class PendingSubmissionItem(BaseModel):
    submission_id: int
    title: str
    abstract: str
    year: int
    supervisor: Optional[str]
    user_name: str
    department: Optional[str]
    tags: List[TagResponse]
    created_at: datetime
    
    class Config:
        from_attributes = True
