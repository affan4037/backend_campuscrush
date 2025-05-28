from typing import List, Optional, Dict
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.modules.posts.reactions.models.reaction import Reaction
from app.modules.posts.reactions.schemas.reaction import ReactionCreate, ReactionCount
from app.modules.notifications.services.notification_events import create_post_like_notification

def get_reaction(db: Session, user_id: str, post_id: str) -> Optional[Reaction]:
    """Get reaction by user ID and post ID"""
    return (
        db.query(Reaction)
        .filter(Reaction.user_id == user_id, Reaction.post_id == post_id)
        .first()
    )

def get_reactions_by_post(db: Session, post_id: str, skip: int = 0, limit: int = 100) -> List[Reaction]:
    """Get reactions by post ID"""
    return (
        db.query(Reaction)
        .filter(Reaction.post_id == post_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_reaction_counts_by_post(db: Session, post_id: str) -> List[ReactionCount]:
    """Get reaction counts by type for a post"""
    counts = (
        db.query(Reaction.reaction_type, func.count(Reaction.id).label("count"))
        .filter(Reaction.post_id == post_id)
        .group_by(Reaction.reaction_type)
        .all()
    )
    
    return [ReactionCount(reaction_type=reaction_type, count=count) for reaction_type, count in counts]

def create_or_update_reaction(db: Session, reaction_in: ReactionCreate, user_id: str) -> Reaction:
    """Create or update a reaction"""
    # Check if user already reacted to this post
    existing_reaction = get_reaction(db, user_id, reaction_in.post_id)
    
    if existing_reaction:
        # Update existing reaction
        existing_reaction.reaction_type = reaction_in.reaction_type
        db.add(existing_reaction)
        db.commit()
        db.refresh(existing_reaction)
        return existing_reaction
    
    # Create new reaction
    reaction = Reaction(
        id=str(uuid.uuid4()),
        user_id=user_id,
        **reaction_in.dict(),
    )
    db.add(reaction)
    db.commit()
    db.refresh(reaction)
    
    # Create notification for the post author
    try:
        create_post_like_notification(db, reaction_in.post_id, user_id)
    except Exception as e:
        # Log the error but don't fail the reaction creation
        print(f"Error creating notification for reaction: {e}")
    
    return reaction

def delete_reaction(db: Session, reaction: Reaction) -> Reaction:
    """Delete reaction"""
    db.delete(reaction)
    db.commit()
    return reaction 