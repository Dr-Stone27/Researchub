from fastapi import APIRouter, Depends, Query, status as http_status
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
from typing import List, Dict, Any
from app import schemas

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/welcome", summary="Personalized welcome message", response_model=Dict[str, str])
async def dashboard_welcome(current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    """
    Async: Returns a personalized greeting for the logged-in user.
    """
    return {"greeting": f"Welcome back, {current_user.name}!"}

@router.get("/user/role", summary="Get user role", response_model=Dict[str, str])
async def dashboard_user_role(current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    """
    Async: Returns the role of the logged-in user.
    """
    return {"role": current_user.role}

@router.get("/user/has-draft", summary="Check if user has draft", response_model=Dict[str, bool])
async def dashboard_user_has_draft(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Dict[str, bool]:
    """
    Async: Returns whether the user has any saved drafts.
    """
    result = await db.execute(select(Draft).filter(Draft.user_id == current_user.id, Draft.status == "draft"))
    has_draft = result.scalars().first() is not None
    return {"has_draft": has_draft}

@router.get("/feed", summary="Dashboard research feed", response_model=List[Dict[str, Any]])
async def dashboard_feed(
    type: str = Query("latest",pattern= "^(latest|trending|featured)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Async: Returns a research feed for the dashboard. Supports 'latest', 'trending', and 'featured' types.
    """
    submissions = []
    if type == "latest":
        result = await db.execute(select(ResearchSubmission).order_by(ResearchSubmission.created_at.desc()).limit(20))
        submissions = result.scalars().all()
    elif type == "featured":
        result = await db.execute(
            select(ResearchSubmission).filter(ResearchSubmission.status == "approved", getattr(ResearchSubmission, "is_featured", False)).order_by(ResearchSubmission.created_at.desc()).limit(20)
        )
        submissions = result.scalars().all()
    elif type == "trending":
        week_ago = datetime.utcnow() - timedelta(days=7)
        activity_counts_result = await db.execute(
            select(UserActivity.target_id, UserActivity.target_type, func.count(UserActivity.id).label("activity_count"))
            .filter(UserActivity.timestamp >= week_ago, UserActivity.target_type == "research", UserActivity.action_type.in_(["view", "download", "save"]))
            .group_by(UserActivity.target_id, UserActivity.target_type)
            .order_by(func.count(UserActivity.id).desc())
            .limit(20)
        )
        activity_counts = activity_counts_result.all()
        trending_ids = [ac.target_id for ac in activity_counts]
        if trending_ids:
            result = await db.execute(select(ResearchSubmission).filter(ResearchSubmission.id.in_(trending_ids)))
            submissions = result.scalars().all()
            submissions = sorted(submissions, key=lambda s: trending_ids.index(s.id))
    feed = []
    for sub in submissions:
        feed.append({
            "id": sub.id,
            "title": sub.title,
            "authors": [sub.user.name] if hasattr(sub, "user") and sub.user else [],
            "department": sub.user.department if hasattr(sub, "user") and sub.user else None,
            "tags": [tag.name for tag in getattr(sub, "tags", [])],
            "is_featured": getattr(sub, "is_featured", False),
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
            "summary": sub.abstract[:200] + ("..." if len(sub.abstract) > 200 else "")
        })
    return feed

@router.get("/user/stats", summary="User discovery and impact stats", response_model=Dict[str, int])
async def dashboard_user_stats(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> Dict[str, int]:
    """
    Async: Returns discovery and impact stats for the logged-in user.
    """
    topics_explored_result = await db.execute(
        select(UserActivity.target_id).filter(
            UserActivity.user_id == current_user.id,
            UserActivity.action_type == "explore_topic"
        ).distinct()
    )
    topics_explored = len(topics_explored_result.scalars().all())
    papers_read_result = await db.execute(
        select(UserActivity).filter(
            UserActivity.user_id == current_user.id,
            UserActivity.action_type == "view",
            UserActivity.target_type == "research"
        )
    )
    papers_read = len(papers_read_result.scalars().all())
    papers_uploaded_result = await db.execute(
        select(ResearchSubmission).filter(
            ResearchSubmission.user_id == current_user.id
        )
    )
    papers_uploaded = len(papers_uploaded_result.scalars().all())
    user_research_ids_result = await db.execute(
        select(ResearchSubmission.id).filter(
            ResearchSubmission.user_id == current_user.id
        )
    )
    user_research_ids = [id for id in user_research_ids_result.scalars().all()]
    total_downloads = 0
    if user_research_ids:
        total_downloads_result = await db.execute(
            select(UserActivity).filter(
                UserActivity.action_type == "download",
                UserActivity.target_type == "research",
                UserActivity.target_id.in_(user_research_ids)
            )
        )
        total_downloads = len(total_downloads_result.scalars().all())
    profile_views_result = await db.execute(
        select(UserActivity).filter(
            UserActivity.action_type == "profile_view",
            UserActivity.target_type == "user",
            UserActivity.target_id == current_user.id
        )
    )
    profile_views = len(profile_views_result.scalars().all())
    return {
        "topics_explored": topics_explored,
        "papers_read": papers_read,
        "papers_uploaded": papers_uploaded,
        "total_downloads": total_downloads,
        "profile_views": profile_views
    }

@router.get("/user/milestones", summary="User milestone progress", response_model=List[Dict[str, Any]])
async def dashboard_user_milestones(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """
    Async: Returns the user's current progress and unlocked milestones.
    """
    milestones_result = await db.execute(select(Milestone))
    milestones = milestones_result.scalars().all()
    user_milestones_result = await db.execute(select(UserMilestone).filter(UserMilestone.user_id == current_user.id))
    user_milestones = {um.milestone_id: um for um in user_milestones_result.scalars().all()}
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
            progress_result = await db.execute(
                select(UserActivity).filter(
                    UserActivity.user_id == current_user.id,
                    UserActivity.action_type == action
                )
            )
            progress = len(progress_result.scalars().all())
        achieved = milestone.id in user_milestones
        achieved_at = user_milestones[milestone.id].achieved_at.isoformat() if achieved else None
        # Notify user if milestone just achieved and not already notified
        if achieved and achieved_at:
            existing_result = await db.execute(
                select(Notification).filter(
                    Notification.user_id == current_user.id,
                    Notification.type == "milestone",
                    Notification.resource_id == milestone.id
                )
            )
            existing = existing_result.scalars().first()
            if not existing:
                await create_notification(db, current_user.id, f"Congratulations! You unlocked the milestone: {milestone.name}", "milestone", resource_id=milestone.id)
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

@router.get("/user/drafts-pending", summary="User drafts and pending submissions", response_model=List[Dict[str, Any]])
async def dashboard_user_drafts_pending(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """
    Async: Returns a list of the user's drafts and pending submissions.
    """
    drafts_result = await db.execute(select(Draft).filter(Draft.user_id == current_user.id, Draft.status == "draft"))
    drafts = drafts_result.scalars().all()
    pending_subs_result = await db.execute(select(ResearchSubmission).filter(ResearchSubmission.user_id == current_user.id, ResearchSubmission.status == "pending"))
    pending_subs = pending_subs_result.scalars().all()
    result = []
    for d in drafts:
        result.append({
            "id": d.id,
            "title": getattr(d.research_submission, "title", None),
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
    return result

@router.get("/user/notifications-latest", summary="Latest user notifications", response_model=List[Dict[str, Any]])
async def dashboard_user_notifications_latest(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """
    Async: Returns the latest 3 notifications for the logged-in user.
    """
    notifications_result = await db.execute(
        select(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(3)
    )
    notifications = notifications_result.scalars().all()
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
async def dashboard_resources(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Async: Returns a list of academic tools/resources for the dashboard.
    """
    resources_result = await db.execute(select(Resource).order_by(Resource.created_at.desc()).limit(10))
    resources = resources_result.scalars().all()
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
async def dashboard_user_onboarding_complete(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> Dict[str, bool]:
    """
    Async: Mark onboarding as complete for the current user.
    """
    current_user.is_first_time = False
    await db.commit()
    return {"success": True} 