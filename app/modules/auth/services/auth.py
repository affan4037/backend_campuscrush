import os
import re
import logging
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from app.modules.user_management.models.user import User
# Import models needed for user deletion
from app.modules.posts.models.post import Post
from app.modules.posts.comments.models.comment import Comment
from app.modules.posts.reactions.models.reaction import Reaction
from app.modules.notifications.models.notification import Notification
from app.modules.friendships.models.friendship import Friendship, FriendshipRequest

logger = logging.getLogger("app")

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()

def _delete_profile_picture(profile_picture_url: str) -> bool:
    """Delete profile picture file if exists"""
    try:
        filename_match = re.search(r'profile_pictures/([^?]+)', profile_picture_url)
        if filename_match:
            filename = filename_match.group(1)
            file_path = Path("uploads/profile_pictures") / filename
            if os.path.exists(file_path):
                logger.info(f"Deleting profile picture: {file_path}")
                os.remove(file_path)
                return True
    except Exception as e:
        logger.error(f"Error deleting profile picture: {e}")
    return False

def delete_user_by_email(db: Session, email: str) -> bool:
    """Delete a user and all related data by email"""
    user = get_user_by_email(db, email=email)
    if not user:
        return False
    
    try:
        user_id = user.id
        
        # Delete profile picture if exists
        if user.profile_picture:
            _delete_profile_picture(user.profile_picture)
        
        # Delete all user-related data in order to handle dependencies
        db.query(Reaction).filter(Reaction.user_id == user_id).delete(synchronize_session=False)
        db.query(Comment).filter(Comment.author_id == user_id).delete(synchronize_session=False)
        db.query(Post).filter(Post.author_id == user_id).delete(synchronize_session=False)
        db.query(Notification).filter(Notification.user_id == user_id).delete(synchronize_session=False)
        
        # Delete friendship requests
        db.query(FriendshipRequest).filter(
            (FriendshipRequest.sender_id == user_id) | 
            (FriendshipRequest.receiver_id == user_id)
        ).delete(synchronize_session=False)
        
        # Delete friendships
        db.query(Friendship).filter(
            (Friendship.user_id == user_id) | 
            (Friendship.friend_id == user_id)
        ).delete(synchronize_session=False)
        
        # Finally delete the user
        db.delete(user)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user: {e}")
        return False 