from typing import List, Optional
import uuid
from sqlalchemy.orm import Session

from app.modules.notifications.models.notification import Notification
from app.modules.notifications.schemas.notification import NotificationCreate, NotificationUpdate, Notification as NotificationSchema
from app.modules.user_management.schemas.user import User as UserSchema
from app.modules.user_management.services.user import get_user

def get_notification(db: Session, notification_id: str) -> Optional[Notification]:
    """Get notification by ID"""
    return db.query(Notification).filter(Notification.id == notification_id).first()

def get_user_notifications(db: Session, user_id: str, skip: int = 0, limit: int = 50, unread_only: bool = False) -> List[NotificationSchema]:
    """Get notifications for a user"""
    query = db.query(Notification).filter(Notification.user_id == user_id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    # Standard notification type mapping for consistent frontend naming
    notification_types_map = {
        "friend_request": "friendshipRequest",
        "friend_accepted": "friendAccepted",
        "post_like": "postLike", 
        "post_comment": "postComment",
        "comment_like": "commentLike"
    }
    
    result = []
    for notification in notifications:
        # Using only Pydantic v1 approach
        notification_dict = notification.__dict__.copy()
        notification_dict.pop("_sa_instance_state", None)
        
        # Add actor information if available
        if notification.actor_id:
            actor = get_user(db, notification.actor_id)
            if actor:
                user_dict = {
                    "id": actor.id,
                    "email": actor.email,
                    "username": actor.username,
                    "full_name": actor.full_name,
                    "bio": actor.bio,
                    "profile_picture": actor.profile_picture,
                    "university": actor.university,
                    "department": actor.department,
                    "graduation_year": actor.graduation_year,
                    "is_active": actor.is_active,
                    "is_verified": actor.is_verified,
                    "created_at": actor.created_at,
                    "updated_at": actor.updated_at
                }
                # Using only Pydantic v1 approach
                notification_dict["actor"] = UserSchema(**user_dict)
        
        # Add related IDs based on notification type
        if notification.type == "post_like":
            notification_dict["post_id"] = notification.related_id
        elif notification.type == "post_comment":
            notification_dict["comment_id"] = notification.related_id
            
            # Get post_id from comment
            try:
                from app.modules.posts.comments.services.comment import get_comment
                comment = get_comment(db, notification.related_id)
                if comment:
                    notification_dict["post_id"] = comment.post_id
            except Exception:
                pass
        
        # Standardize notification type names for frontend
        if notification.type in notification_types_map:
            notification_dict["type"] = notification_types_map[notification.type]
        
        # Using only Pydantic v1 approach
        result.append(NotificationSchema(**notification_dict))
    
    return result

def create_notification(db: Session, notification_in: NotificationCreate) -> Notification:
    """Create a new notification"""
#    Acessing notification_in object data using dict() method
    notification_data = notification_in.dict()
    
    notification = Notification(
        id=str(uuid.uuid4()),
        **notification_data,
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification

def update_notification(db: Session, notification: Notification, notification_in: NotificationUpdate) -> Notification:
    """Update a notification"""
    notification.is_read = notification_in.is_read
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification

def mark_all_as_read(db: Session, user_id: str) -> int:
    """Mark all notifications as read for a user"""
    result = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    
    return result

def delete_notification(db: Session, notification: Notification) -> Notification:
    """Delete a notification"""
    db.delete(notification)
    db.commit()
    
    return notification

def delete_all_notifications(db: Session, user_id: str) -> int:
    """Delete all notifications for a user"""
    result = db.query(Notification).filter(Notification.user_id == user_id).delete()
    db.commit()
    
    return result 

