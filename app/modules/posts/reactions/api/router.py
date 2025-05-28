from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_active_verified_user
from app.modules.user_management.models.user import User
from app.modules.posts.services.post import get_post
from app.modules.posts.reactions.schemas.reaction import (
    Reaction as ReactionSchema, ReactionCreate, ReactionCount
)
from app.modules.posts.reactions.services.reaction import (
    get_reaction, get_reactions_by_post, get_reaction_counts_by_post,
    create_or_update_reaction, delete_reaction
)

router = APIRouter()

def _validate_post(db: Session, post_id: str) -> None:
    """Validate post exists or raise HTTPException"""
    post = get_post(db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

def _validate_reaction(db: Session, user_id: str, post_id: str) -> Any:
    """Validate reaction exists and return it or raise HTTPException"""
    reaction = get_reaction(db, user_id, post_id)
    if not reaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reaction not found"
        )
    return reaction

@router.post("", response_model=ReactionSchema)
def create_or_update_post_reaction(
    *,
    db: Session = Depends(get_db),
    post_id: str = Path(..., description="The ID of the post to react to"),
    reaction_in: ReactionCreate,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Create or update a reaction to a post"""
    _validate_post(db, post_id)
    
    reaction_data = ReactionCreate(
        reaction_type=reaction_in.reaction_type,
        post_id=post_id
    )
    
    return create_or_update_reaction(db, reaction_data, current_user.id)
    
@router.get("", response_model=List[ReactionSchema])
def read_reactions_by_post_id(
    *,
    db: Session = Depends(get_db),
    post_id: str = Path(..., description="The ID of the post to get reactions for"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Get reactions by post ID"""
    _validate_post(db, post_id)
    
    return get_reactions_by_post(db, post_id=post_id, skip=skip, limit=limit)
    
@router.get("/counts", response_model=List[ReactionCount])
def read_reaction_counts_by_post_id(
    *,
    db: Session = Depends(get_db),
    post_id: str = Path(..., description="The ID of the post to get reaction counts for"),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Get reaction counts by type for a post"""
    _validate_post(db, post_id)
    
    return get_reaction_counts_by_post(db, post_id=post_id)

@router.delete("", response_model=ReactionSchema)
def delete_post_reaction(
    *,
    db: Session = Depends(get_db),
    post_id: str = Path(..., description="The ID of the post to remove reaction from"),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Delete a reaction from a post by the current user"""
    _validate_post(db, post_id)
    reaction = _validate_reaction(db, current_user.id, post_id)
    
    return delete_reaction(db, reaction)
