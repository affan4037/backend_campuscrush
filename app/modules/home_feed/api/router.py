from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_active_verified_user
from app.modules.user_management.models.user import User
from app.modules.home_feed.schemas.feed import FeedResponse
from app.modules.home_feed.services.feed import get_home_feed

router = APIRouter()

@router.get("/", response_model=FeedResponse)
@router.get("", response_model=FeedResponse)
def read_home_feed(
    *,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Get personalized home feed for the current user with pagination"""
    return get_home_feed(db, current_user.id, skip, limit) 