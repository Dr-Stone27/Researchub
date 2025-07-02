"""
models.py

SQLAlchemy ORM models for the Research Resource Hub backend.
Defines User, ResearchSubmission, Tag, Notification, Resource, and association tables.
All relationships and fields are documented for clarity and auditability.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Table, Boolean
from sqlalchemy.orm import relationship, declarative_base
import datetime

Base = declarative_base()

# User, Research, Tag models will be defined here 

# Association table for many-to-many between ResearchSubmission and Tag
submission_tag_association = Table(
    'submission_tag_association', Base.metadata,
    Column('submission_id', Integer, ForeignKey('research_submissions.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

# Association table for many-to-many between Resource and Tag
define_resource_tag_association = Table(
    'resource_tag_association', Base.metadata,
    Column('resource_id', Integer, ForeignKey('resources.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class User(Base):
    """
    User model: represents a user in the system (student, contributor, admin).
    Relationships: submissions (research), notifications, resources (created).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    matric_or_faculty_id = Column(String(50), unique=True, index=True, nullable=True)
    department = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True, unique=True)
    verification_token_expiry = Column(DateTime, nullable=True)
    account_status = Column(String(32), default="pending_verification")
    role = Column(String(20), default="student")  # student, contributor, admin
    first_login = Column(DateTime, nullable=True)  # Timestamp of first successful login
    last_login = Column(DateTime, nullable=True)   # Timestamp of most recent login
    password_reset_token = Column(String(255), nullable=True, unique=True)  # For password reset
    password_reset_token_expiry = Column(DateTime, nullable=True)           # Expiry for reset token
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    submissions = relationship("ResearchSubmission", back_populates="user")  # One-to-many
    # notifications and resources: see backrefs in Notification/Resource
    is_first_time = Column(Boolean, default=True)  # Tracks if user is a first-time user for onboarding
    token_version = Column(Integer, default=0)  # For JWT token revocation/versioning

class ResearchSubmission(Base):
    """
    ResearchSubmission model: represents a research project submitted by a user.
    Linked to tags (many-to-many) and user (many-to-one).
    """
    __tablename__ = "research_submissions"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    abstract = Column(String(2000), nullable=False)
    supervisor = Column(String(100), nullable=True)
    year = Column(Integer, nullable=False)
    file_url = Column(String(500), nullable=False)
    status = Column(String(20), default="pending")  # pending, approved, rejected
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user = relationship("User", back_populates="submissions")
    tags = relationship("Tag", secondary=submission_tag_association, back_populates="submissions")

class Tag(Base):
    """
    Tag model: multi-category tags for research and resources.
    Can be core (faculty-approved) or suggested by students.
    Linked to submissions and resources (many-to-many).
    """
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50), nullable=False)  # department, subject_area, method, application, technology
    type = Column(String(20), default="suggested")  # core, suggested
    status = Column(String(20), default="pending")  # approved, pending, rejected
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    submissions = relationship("ResearchSubmission", secondary=submission_tag_association, back_populates="tags")
    resources = relationship("Resource", secondary=define_resource_tag_association, back_populates="tags")

class Notification(Base):
    """
    Notification model: user notifications for system events, resource updates, etc.
    Linked to user (many-to-one) and optionally to a resource.
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    resource_id = Column(Integer, nullable=True)  # Can be linked to guides/resources later
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", backref="notifications")

class Resource(Base):
    """
    Resource model: guides, templates, and other resources.
    Linked to tags (many-to-many) and user (creator, many-to-one).
    """
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)  # guide, template, etc.
    content_url = Column(String(500), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user = relationship("User", backref="resources")
    tags = relationship("Tag", secondary=define_resource_tag_association, back_populates="resources") 

class Draft(Base):
    """
    Draft model: represents a draft or incomplete research submission by a user.
    Linked to user and research submission.
    """
    __tablename__ = "drafts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    research_submission_id = Column(Integer, ForeignKey("research_submissions.id"), nullable=True, index=True)
    status = Column(String(20), default="draft")  # draft, pending, submitted
    last_edited = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", backref="drafts")
    research_submission = relationship("ResearchSubmission", backref="drafts")

class UserActivity(Base):
    """
    UserActivity model: logs user actions for analytics, stats, and gamification.
    Extensible via metadata JSON field.
    """
    __tablename__ = "user_activities"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False, index=True)  # view, download, save, submit, etc.
    target_type = Column(String(50), nullable=True)  # research, topic, milestone, etc.
    target_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    metadata = Column(String, nullable=True)  # JSON as string for extensibility
    user = relationship("User", backref="activities")

class Milestone(Base):
    """
    Milestone model: defines all possible milestones for gamification.
    Criteria stored as JSON for flexibility.
    """
    __tablename__ = "milestones"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    criteria = Column(String, nullable=False)  # JSON as string
    badge_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class UserMilestone(Base):
    """
    UserMilestone model: tracks which milestones a user has achieved.
    Linked to user and milestone.
    """
    __tablename__ = "user_milestones"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False, index=True)
    achieved_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", backref="user_milestones")
    milestone = relationship("Milestone", backref="user_milestones") 