from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.deps import get_current_active_verified_user
from app.modules.user_management.models.user import User
from app.modules.user_management.schemas.user import User as UserSchema
from app.modules.user_management.services.user import get_user
from app.modules.posts.services.post import get_post
from app.modules.posts.comments.schemas.comment import (
    Comment as CommentSchema, CommentCreate, CommentUpdate, CommentWithReplies
)
from app.modules.posts.comments.services.comment import (
    get_comment, get_comments_by_post, get_comment_replies, get_comments_with_replies,
    create_comment, update_comment, delete_comment, get_latest_comment
)

router = APIRouter()
logger = logging.getLogger("app")

def _validate_post(db: Session, post_id: str) -> None:
    """Validate post exists and return None or raise HTTPException"""
    post = get_post(db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

def _validate_comment(db: Session, comment_id: str, post_id: str = None) -> Any:
    """Validate comment exists, belongs to post if specified, and return comment or raise HTTPException"""
    comment = get_comment(db, comment_id=comment_id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    if post_id and comment.post_id != post_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment does not belong to the specified post"
        )
    
    return comment

def _validate_ownership(comment: Any, user_id: str) -> None:
    """Validate user is the author of the comment or raise HTTPException"""
    if comment.author_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

def _ensure_author_in_comment(db: Session, comment_data: Dict) -> Dict:
    """Ensure the comment data includes author information"""
    # Clone the comment data
    enhanced_comment = dict(comment_data)
    
    # If author field is missing, retrieve user data and add it
    if "author" not in enhanced_comment and "author_id" in enhanced_comment:
        author_id = enhanced_comment["author_id"]
        user_db = get_user(db, user_id=author_id)
        
        if user_db:
            try:
                # Create user schema
                user_schema = UserSchema(
                    id=user_db.id,
                    username=user_db.username,
                    email=user_db.email,
                    full_name=user_db.full_name,
                    university=user_db.university,
                    profile_picture=user_db.profile_picture,
                    is_active=user_db.is_active,
                    is_verified=user_db.is_verified,
                    created_at=user_db.created_at,
                    updated_at=user_db.updated_at,
                )
                enhanced_comment["author"] = user_schema
            except Exception as e:
                logger.error(f"Error creating user schema in _ensure_author_in_comment: {str(e)}")
    
    return enhanced_comment

def _prepare_comment_response(db: Session, comment) -> Dict:
  
    if hasattr(comment, 'dict'):
        comment_dict = comment.dict()
    else:
        comment_dict = {
            "id": comment.id,
            "content": comment.content,
            "author_id": comment.author_id,
            "post_id": comment.post_id,
            "parent_id": comment.parent_id,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
        }
    return _ensure_author_in_comment(db, comment_dict)

@router.post("", response_model=CommentSchema)
def create_new_comment(
    *,
    db: Session = Depends(get_db),
    post_id: str = Path(..., description="The ID of the post to comment on"),
    comment_in: CommentCreate,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Create new comment on a post"""
    try:
        _validate_post(db, post_id)
        
        comment_data = CommentCreate(
            content=comment_in.content,
            post_id=post_id,
            parent_id=comment_in.parent_id
        )
        
        if comment_data.parent_id:
            _validate_comment(db, comment_data.parent_id, post_id)
        
        comment = create_comment(db, comment_data, current_user.id)
        
        return _prepare_comment_response(db, comment)
    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment"
        )

@router.get("", response_model=List[CommentWithReplies])
def read_comments_by_post_id(
    *,
    db: Session = Depends(get_db),
    post_id: str = Path(..., description="The ID of the post to get comments for"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Get comments by post ID with replies"""
    _validate_post(db, post_id)
    comments_with_replies = get_comments_with_replies(db, post_id=post_id, skip=skip, limit=limit)
    
    # Make sure each comment and reply has author information
    for comment in comments_with_replies:
        
        comment_dict = comment.dict()
        if "author" not in comment_dict:
            comment.author = _ensure_author_in_comment(db, comment_dict).get("author")
        
        for reply in comment.replies:
            
            reply_dict = reply.dict()
            if "author" not in reply_dict:
                reply.author = _ensure_author_in_comment(db, reply_dict).get("author")
    
    return comments_with_replies

@router.get("/latest", response_model=CommentSchema)
def read_latest_comment(
    *,
    db: Session = Depends(get_db),
    post_id: str = Path(..., description="The ID of the post"),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Get the latest comment for a post"""
    try:
        _validate_post(db, post_id)
        
        latest_comment = get_latest_comment(db, post_id=post_id)
        if not latest_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No comments found for this post"
            )
        
        # Ensure author info is included
        return _prepare_comment_response(db, latest_comment)
    except Exception as e:
        logger.error(f"Error getting latest comment: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get latest comment"
        )

@router.get("/{comment_id}/replies", response_model=List[CommentSchema])
def read_comment_replies_by_id(
    *,
    db: Session = Depends(get_db),
    post_id: str = Path(..., description="The ID of the post"),
    comment_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Get replies to a comment"""
    try:
        _validate_post(db, post_id)
        _validate_comment(db, comment_id, post_id)
        
        replies = get_comment_replies(db, comment_id=comment_id, skip=skip, limit=limit)
        
        # Ensure each reply has author information
        return [_prepare_comment_response(db, reply) for reply in replies]
    except Exception as e:
        logger.error(f"Error getting comment replies: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get comment replies"
        )

@router.put("/{comment_id}", response_model=CommentSchema)
def update_comment_by_id(
    *,
    db: Session = Depends(get_db),
    post_id: str = Path(..., description="The ID of the post"),
    comment_id: str,
    comment_in: CommentUpdate,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Update a comment"""
    try:
        _validate_post(db, post_id)
        comment = _validate_comment(db, comment_id, post_id)
        _validate_ownership(comment, current_user.id)
        
        updated_comment = update_comment(db, comment, comment_in)
        
        # Ensure author info is included
        return _prepare_comment_response(db, updated_comment)
    except Exception as e:
        logger.error(f"Error updating comment: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update comment"
        )

@router.delete("/{comment_id}", response_model=CommentSchema)
def delete_comment_by_id(
    *,
    db: Session = Depends(get_db),
    post_id: str = Path(..., description="The ID of the post"),
    comment_id: str,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Delete a comment"""
    try:
        _validate_post(db, post_id)
        comment = _validate_comment(db, comment_id, post_id)
        _validate_ownership(comment, current_user.id)
        
        deleted_comment = delete_comment(db, comment)
        
        # For consistency, ensure the response includes author info
        return _prepare_comment_response(db, deleted_comment)
    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete comment"
        ) 