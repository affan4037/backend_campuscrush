"""
Notification events service.
This module handles the creation of notifications for various events in the application.
"""
from sqlalchemy.orm import Session
import logging

from app.modules.notifications.services.notification import create_notification
from app.modules.notifications.schemas.notification import NotificationCreate
from app.modules.posts.services.post import get_post
from app.modules.user_management.services.user import get_user
from app.modules.notifications.models.notification import Notification
# Set up logger
logger = logging.getLogger(__name__)

def create_post_like_notification(db: Session, post_id: str, liker_id: str) -> bool:
    """
    Create a notification when a post is liked.
    
    Args:
        db: Database session
        post_id: ID of the post that was liked
        liker_id: ID of the user who liked the post
        
    Returns:
        True if notification was created, False otherwise
    """
    try:
        # Get the post
        post = get_post(db, post_id)
        if not post:
            logger.warning(f"Post {post_id} not found when creating like notification")
            return False
            
        # Get the post author
        post_author_id = post.author_id
        
        # Don't notify if the liker is the post author
        if post_author_id == liker_id:
            logger.debug(f"User {liker_id} liked their own post, no notification created")
            return False
            
        # Get the liker
        liker = get_user(db, liker_id)
        if not liker:
            logger.warning(f"User {liker_id} not found when creating like notification")
            return False
            
        # Create notification data
        notification_data = NotificationCreate(
            user_id=post_author_id,
            actor_id=liker_id,
            type="post_like",
            content=f"{liker.username} liked your post",
            related_id=post_id
        )
        
        # Create the notification
        create_notification(db, notification_data)
        logger.info(f"Created post like notification for user {post_author_id} from user {liker_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating post like notification: {e}")
        return False

def create_post_comment_notification(db: Session, post_id: str, comment_id: str, commenter_id: str) -> bool:
    """
    Create a notification when a post is commented on.
    
    Args:
        db: Database session
        post_id: ID of the post that was commented on
        comment_id: ID of the comment
        commenter_id: ID of the user who commented
        
    Returns:
        True if notification was created, False otherwise
    """
    try:
        # Get the post
        post = get_post(db, post_id)
        if not post:
            logger.warning(f"Post {post_id} not found when creating comment notification")
            return False
            
        # Get the post author
        post_author_id = post.author_id
        
        # Don't notify if the commenter is the post author
        if post_author_id == commenter_id:
            logger.debug(f"User {commenter_id} commented on their own post, no notification created")
            return False
            
        # Get the commenter
        commenter = get_user(db, commenter_id)
        if not commenter:
            logger.warning(f"User {commenter_id} not found when creating comment notification")
            return False
            
        # Create notification data
        notification_data = NotificationCreate(
            user_id=post_author_id,
            actor_id=commenter_id,
            type="post_comment",
            content=f"{commenter.username} commented on your post",
            related_id=comment_id
        )
        
        # Store the post ID in a separate field
        try:
            notification = create_notification(db, notification_data)
            
            # Add post_id to a new field or metadata if possible
            # Since we only have related_id in the Notification model, we'll rely on
            # the get_user_notifications service to populate the post_id from the comment
            
            logger.info(f"Created post comment notification for user {post_author_id} from user {commenter_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing post_id for comment notification: {e}")
            return False
        
    except Exception as e:
        logger.error(f"Error creating post comment notification: {e}")
        return False

def create_friend_request_notification(db: Session, sender_id: str, receiver_id: str, request_id: str) -> bool:
    """
    Create a notification when a friend request is sent.
    
    Args:
        db: Database session
        sender_id: ID of the user who sent the request
        receiver_id: ID of the user who received the request
        request_id: ID of the friend request
        
    Returns:
        True if notification was created, False otherwise
    """
    try:
        # Get the sender
        sender = get_user(db, sender_id)
        if not sender:
            logger.warning(f"User {sender_id} not found when creating friend request notification")
            return False
            
        # Create notification data
        notification_data = NotificationCreate(
            user_id=receiver_id,
            actor_id=sender_id,
            type="friend_request",
            content=f"{sender.username} sent you a friend request",
            related_id=request_id
        )
        
        # Create the notification
        create_notification(db, notification_data)
        logger.info(f"Created friend request notification for user {receiver_id} from user {sender_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating friend request notification: {e}")
        return False

def create_friend_request_accepted_notification(db: Session, accepter_id: str, requester_id: str) -> bool:
    """
    Create a notification when a friend request is accepted.
    
    Args:
        db: Database session
        accepter_id: ID of the user who accepted the request
        requester_id: ID of the user who sent the original request
        
    Returns:
        True if notification was created, False otherwise
    """
    try:
        # Get the accepter
        accepter = get_user(db, accepter_id)
        if not accepter:
            logger.warning(f"User {accepter_id} not found when creating friend accepted notification")
            return False
            
        # Create notification data
        notification_data = NotificationCreate(
            user_id=requester_id,
            actor_id=accepter_id,
            type="friend_accepted",
            content=f"{accepter.username} accepted your friend request",
            related_id=None
        )
        
        # Create the notification
        create_notification(db, notification_data)
        logger.info(f"Created friend request accepted notification for user {requester_id} from user {accepter_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating friend request accepted notification: {e}")
        return False 