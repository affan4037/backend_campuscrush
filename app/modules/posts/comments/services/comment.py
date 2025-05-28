from typing import List, Optional
import uuid
from sqlalchemy.orm import Session, joinedload

from app.modules.posts.comments.models.comment import Comment
from app.modules.posts.comments.schemas.comment import CommentCreate, CommentUpdate, CommentWithReplies, Comment as CommentSchema
from app.modules.user_management.models.user import User as UserModel
from app.modules.user_management.schemas.user import User as UserSchema

def get_comment(db: Session, comment_id: str) -> Optional[Comment]:
    """Get comment by ID"""
    return db.query(Comment).filter(Comment.id == comment_id).first()

def get_comments_by_post(db: Session, post_id: str, skip: int = 0, limit: int = 100) -> List[Comment]:
    """Get top-level comments by post ID"""
    return (
        db.query(Comment)
        .filter(Comment.post_id == post_id, Comment.parent_id == None)
        .order_by(Comment.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_comment_replies(db: Session, comment_id: str, skip: int = 0, limit: int = 100) -> List[Comment]:
    """Get replies to a comment"""
    return (
        db.query(Comment)
        .filter(Comment.parent_id == comment_id)
        .order_by(Comment.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def _get_comment_with_author(db: Session, comment: Comment) -> CommentSchema:
    """Helper to convert a Comment model to CommentSchema with author"""
    author = db.query(UserModel).filter(UserModel.id == comment.author_id).first()
    
    # Using only Pydantic v1 approach
    author_schema = None
    if author:
        author_dict = author.__dict__.copy()
        if "_sa_instance_state" in author_dict:
            author_dict.pop("_sa_instance_state")
        author_schema = UserSchema(**author_dict)
    
    # Create comment schema with author
    return CommentSchema(
        id=comment.id,
        content=comment.content,
        author_id=comment.author_id,
        post_id=comment.post_id,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author=author_schema,
        like_count=0,  # These fields can be calculated if needed
        has_liked=False,
        replies_count=0,
        is_edited=comment.updated_at > comment.created_at,
    )

def get_comments_with_replies(db: Session, post_id: str, skip: int = 0, limit: int = 100) -> List[CommentWithReplies]:
    """Get comments with their replies"""
    comments = get_comments_by_post(db, post_id, skip, limit)
    result = []
    
    for comment in comments:
        comment_schema = _get_comment_with_author(db, comment)
        
        # Get replies
        reply_models = get_comment_replies(db, comment.id)
        replies = [_get_comment_with_author(db, reply) for reply in reply_models]
        
        # Set replies count
        comment_schema.replies_count = len(replies)
        
        # Create the comment with replies
        result.append(CommentWithReplies(
            **comment_schema.dict(),
            replies=replies
        ))
    
    return result

def create_comment(db: Session, comment_in: CommentCreate, author_id: str) -> CommentSchema:
    """Create a new comment"""
    # Extract data from schema using Pydantic v1
    comment_data = comment_in.dict()
    
    # Create and save comment
    comment = Comment(
        id=str(uuid.uuid4()),
        author_id=author_id,
        **comment_data,
    )
    
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    # Create notification for the post author
    try:
        from app.modules.notifications.services.notification_events import create_post_comment_notification
        create_post_comment_notification(db, comment_data['post_id'], comment.id, author_id)
    except Exception as e:
        # Log error but don't fail comment creation
        import logging
        logging.error(f"Error creating notification for comment: {e}")
    
    # Return comment with author
    return _get_comment_with_author(db, comment)

def update_comment(db: Session, comment: Comment, comment_in: CommentUpdate) -> CommentSchema:
    """Update comment"""
    update_data = comment_in.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(comment, field, value)
    
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return _get_comment_with_author(db, comment)

def delete_comment(db: Session, comment: Comment) -> Comment:
    """Delete comment"""
    db.delete(comment)
    db.commit()
    return comment

def get_latest_comment(db: Session, post_id: str) -> Optional[CommentSchema]:
    """Get the latest comment for a post"""
    latest_comment = (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.desc())
        .first()
    )
    
    if not latest_comment:
        return None
    
    return _get_comment_with_author(db, latest_comment) 