from fastapi import APIRouter, Depends, Query, status as http_status, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.auth import get_current_user
from app.models import (
    User, Draft, ResearchSubmission, Tag, UserActivity, Milestone, UserMilestone, Notification, Resource
)
from app.database import get_db
from datetime import datetime, timedelta
import json
from app.utils import create_notification
from typing import List, Dict, Any, Optional
from app import schemas
# Add this import
from sqlalchemy import distinct


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Add security dependency for all endpoints
oauth2_scheme = HTTPBearer(auto_error=False)

@router.get("/welcome", summary="Personalized welcome message", response_model=Dict[str, str])
async def dashboard_welcome(
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)  # Add security dependency
) -> Dict[str, str]:
    """
    Async: Returns a personalized greeting for the logged-in user.
    """
    return {"greeting": f"Welcome back, {current_user.name}!"}

@router.get("/user/role", summary="Get user role", response_model=Dict[str, str])
async def dashboard_user_role(
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)  # Add security dependency
) -> Dict[str, str]:
    """
    Async: Returns the role of the logged-in user.
    """
    return {"role": current_user.role}

@router.get("/user/has-draft", summary="Check if user has draft", response_model=Dict[str, bool])
async def dashboard_user_has_draft(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)  # Add security dependency
) -> Dict[str, bool]:
    """
    Async: Returns whether the user has any saved drafts.
    """
    result = await db.execute(
        select(func.count(Draft.id))
        .filter(Draft.user_id == current_user.id, Draft.status == "draft")
    )
    count = result.scalar()
    return {"has_draft": count > 0}

@router.get("/feed", summary="Dashboard research feed", response_model=List[Dict[str, Any]])
async def dashboard_feed(
    type: str = Query("latest", pattern="^(latest|trending|featured)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)  # Add security dependency
) -> List[Dict[str, Any]]:
    """
    Async: Returns a research feed for the dashboard. Supports 'latest', 'trending', and 'featured' types.
    """
    # Use efficient queries with joins
    base_query = select(
        ResearchSubmission.id,
        ResearchSubmission.title,
        ResearchSubmission.abstract,
        ResearchSubmission.created_at,
        # ResearchSubmission.is_featured,
        User.name.label("author_name"),
        User.department
    ).join(User, ResearchSubmission.user_id == User.id)
    
    if type == "latest":
        result = await db.execute(
            base_query
            .order_by(ResearchSubmission.created_at.desc())
            .limit(20)
        )
    elif type == "featured":
        result = await db.execute(
            base_query
            .filter(ResearchSubmission.status == "approved", ResearchSubmission.is_featured)
            .order_by(ResearchSubmission.created_at.desc())
            .limit(20)
        )
    elif type == "trending":
        week_ago = datetime.utcnow() - timedelta(days=7)
        trending_subquery = select(
                UserActivity.target_id,
                func.count(UserActivity.id).label("activity_count")
            .filter(
                UserActivity.timestamp >= week_ago,
                UserActivity.target_type == "research",
                UserActivity.action_type.in_(["view", "download", "save"])
            )
            .group_by(UserActivity.target_id)
            .order_by(func.count(UserActivity.id).desc())
            .limit(20)
            .subquery()
            )
        
        result = await db.execute(
            base_query
            .join(trending_subquery, ResearchSubmission.id == trending_subquery.c.target_id)
            .order_by(trending_subquery.c.activity_count.desc())
        )
    
    submissions = result.all()
    
    # Get tags in bulk for efficiency
    submission_ids = [sub.id for sub in submissions]
    tags_result = await db.execute(
        select(ResearchSubmission.id, Tag.name)
        .join(ResearchSubmission.tags)
        .filter(ResearchSubmission.id.in_(submission_ids)))
    tags_map = {}
    for sub_id, tag_name in tags_result:
        tags_map.setdefault(sub_id, []).append(tag_name)
    
    # Build response
    feed = []
    for sub in submissions:
        feed.append({
            "id": sub.id,
            "title": sub.title,
            "authors": [sub.author_name] if sub.author_name else [],
            "department": sub.department,
            "tags": tags_map.get(sub.id, []),
            "is_featured": sub.is_featured,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
            "summary": (sub.abstract[:200] + "...") if sub.abstract and len(sub.abstract) > 200 else (sub.abstract or "")
        })
    
    return feed

@router.get("/user/stats", summary="User discovery and impact stats", response_model=Dict[str, int])
async def dashboard_user_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)  # Add security dependency
) -> Dict[str, int]:
    """
    Async: Returns discovery and impact stats for the logged-in user.
    """
    # Use count() for better performance
    topics_explored = await db.scalar(
        select(func.count(distinct(UserActivity.target_id)))
        .filter(
            UserActivity.user_id == current_user.id,
            UserActivity.action_type == "explore_topic"
        )
    ) or 0
    
    papers_read = await db.scalar(
        select(func.count(UserActivity.id))
        .filter(
            UserActivity.user_id == current_user.id,
            UserActivity.action_type == "view",
            UserActivity.target_type == "research"
        )
    ) or 0
    
    papers_uploaded = await db.scalar(
        select(func.count(ResearchSubmission.id))
        .filter(ResearchSubmission.user_id == current_user.id)
    ) or 0
    
    total_downloads = await db.scalar(
        select(func.count(UserActivity.id))
        .filter(
            UserActivity.action_type == "download",
            UserActivity.target_type == "research",
            UserActivity.target_id.in_(
                select(ResearchSubmission.id)
                .filter(ResearchSubmission.user_id == current_user.id)
            )
        )
    ) or 0
    
    profile_views = await db.scalar(
        select(func.count(UserActivity.id))
        .filter(
            UserActivity.action_type == "profile_view",
            UserActivity.target_type == "user",
            UserActivity.target_id == current_user.id
        )
    ) or 0
    
    return {
        "topics_explored": topics_explored,
        "papers_read": papers_read,
        "papers_uploaded": papers_uploaded,
        "total_downloads": total_downloads,
        "profile_views": profile_views
    }

@router.get("/user/milestones", summary="User milestone progress", response_model=List[Dict[str, Any]])
async def dashboard_user_milestones(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)  # Add security dependency
) -> List[Dict[str, Any]]:
    """
    Async: Returns the user's current progress and unlocked milestones.
    """
    milestones = await db.scalars(select(Milestone))
    user_milestones = {
        um.milestone_id: um 
        for um in await db.scalars(
            select(UserMilestone)
            .filter(UserMilestone.user_id == current_user.id)
        )
    }
    
    result = []
    for milestone in milestones:
        try:
            criteria = json.loads(milestone.criteria)
        except Exception:
            criteria = {}
        
        action = criteria.get("action")
        target = criteria.get("count", 1)
        progress = 0
        
        if action:
            progress = await db.scalar(
                select(func.count(UserActivity.id))
                .filter(
                    UserActivity.user_id == current_user.id,
                    UserActivity.action_type == action
                )
            ) or 0
        
        um = user_milestones.get(milestone.id)
        achieved = um is not None
        achieved_at = um.achieved_at.isoformat() if achieved and um.achieved_at else None
        
        # Only create notification if milestone was just achieved
        if achieved and not um.notified:
            await create_notification(
                db, current_user.id, 
                f"Congratulations! You unlocked the milestone: {milestone.name}", 
                "milestone", 
                resource_id=milestone.id
            )
            um.notified = True
            await db.commit()
        
        result.append({
            "milestone_id": milestone.id,
            "name": milestone.name,
            "description": milestone.description,
            "badge_url": milestone.badge_url,
            "achieved": achieved,
            "progress": progress,
            "target": target,
            "achieved_at": achieved_at
        })
    
    return result

@router.get("/user/drafts-pending", summary="User drafts and pending submissions", response_model=List[schemas.DraftResponse])
async def dashboard_user_drafts_pending(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)  # Add security dependency
) -> List[Dict[str, Any]]:
    """
    Async: Returns a list of the user's drafts and pending submissions.
    """
    drafts = await db.scalars(
        select(Draft)
        .filter(Draft.user_id == current_user.id, Draft.status == "draft")
    )
    
    pending_subs = await db.scalars(
        select(ResearchSubmission)
        .filter(
            ResearchSubmission.user_id == current_user.id, 
            ResearchSubmission.status == "pending"
        )
    )
    
    result = []
    for d in drafts:
        result.append({
            "id": d.id,
            "title": getattr(d.research_submission, "title", None) or "Untitled Draft",
            "status": d.status,
            "last_edited": d.last_edited.isoformat() if d.last_edited else None,
            "is_draft": True
        })
    
    for s in pending_subs:
        result.append({
            "id": s.id,
            "title": s.title,
            "status": s.status,
            "last_edited": s.updated_at.isoformat() if s.updated_at else None,
            "is_draft": False
        })
    
    return sorted(result, key=lambda x: x["last_edited"] or "", reverse=True)

@router.get("/user/notifications-latest", summary="Latest user notifications", response_model=List[Dict[str, Any]])
async def dashboard_user_notifications_latest(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)  # Add security dependency
) -> List[Dict[str, Any]]:
    """
    Async: Returns the latest 3 notifications for the logged-in user.
    """
    notifications = await db.scalars(
        select(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(3)
    )
    
    return [
        {
            "id": n.id,
            "message": n.message,
            "type": n.type,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "read": n.is_read
        }
        for n in notifications
    ]

@router.get("/resources", summary="Dashboard academic resources", response_model=List[Dict[str, Any]])
async def dashboard_resources(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)  # Add security dependency
) -> List[Dict[str, Any]]:
    """
    Async: Returns a list of academic tools/resources for the dashboard.
    """
    resources = await db.scalars(
        select(Resource)
        .order_by(Resource.created_at.desc())
        .limit(10)
    )
    
    return [
        {
            "id": r.id,
            "title": r.title,
            "type": r.type,
            "url": r.content_url,
            "description": r.description,
            "audience": getattr(r, "audience", "all")
        }
        for r in resources
    ]

@router.post("/user/onboarding-complete", summary="Mark onboarding as complete", response_model=Dict[str, bool], status_code=http_status.HTTP_200_OK)
async def dashboard_user_onboarding_complete(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)  # Add security dependency
) -> Dict[str, bool]:
    """
    Async: Mark onboarding as complete for the current user.
    """
    if not current_user.is_first_time:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already marked as complete"
        )
        
    current_user.is_first_time = False
    await db.commit()
    await db.refresh(current_user)

    return {"success": True}