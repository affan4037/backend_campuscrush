from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
import os
import re

from app.modules.posts.models.post import Post
from app.modules.posts.schemas.post import PostCreate, PostUpdate, PostWithCounts
from app.modules.posts.comments.models.comment import Comment
from app.modules.posts.reactions.models.reaction import Reaction
from app.core.config import settings

def _fix_media_url(media_url: str) -> str:
    """If R2 is configured, always rewrite any local/proxy/static URL to the R2 public URL."""
    if not media_url:
        return media_url
    if settings.R2_PUBLIC_URL:
        # Extract the filename from any known pattern
        # Match /static/post_media/ or /media/post_media/ or /post_media/ or just the filename
        match = re.search(r"(?:/static/post_media/|/media/post_media/|/post_media/)?([a-f0-9]{32,}[^/?]*)", media_url)
        if match:
            filename = match.group(1)
            return f"{settings.R2_PUBLIC_URL}/post_media/{filename}"
    return media_url

def get_post(db: Session, post_id: str) -> Optional[Post]:
    """Get post by ID"""
    logging.info(f"Getting post with ID: {post_id}")
    post = db.query(Post).filter(Post.id == post_id).first()
    if post and post.media_url:
        post.media_url = _fix_media_url(post.media_url)
    return post

def get_posts(db: Session, skip: int = 0, limit: int = 20) -> List[Post]:
    """Get list of posts"""
    logging.info(f"Getting posts with skip={skip}, limit={limit}")
    return db.query(Post).order_by(Post.created_at.desc()).offset(skip).limit(limit).all()

def get_posts_with_counts(db: Session, skip: int = 0, limit: int = 20) -> List[PostWithCounts]:
    """Get list of posts with comment and reaction counts"""
    logging.info(f"Getting posts with counts with skip={skip}, limit={limit}")
    posts = get_posts(db, skip, limit)
    result = []
    
    for post in posts:
        comment_count = db.query(func.count(Comment.id)).filter(Comment.post_id == post.id).scalar() or 0
        reaction_count = db.query(func.count(Reaction.id)).filter(Reaction.post_id == post.id).scalar() or 0
        
        post_dict = {
            **post.__dict__,
            "comment_count": comment_count,
            "reaction_count": reaction_count
        }
        
        # Remove SQLAlchemy state
        if "_sa_instance_state" in post_dict:
            del post_dict["_sa_instance_state"]
            
        # Fix media_url if needed
        if post_dict.get("media_url"):
            post_dict["media_url"] = _fix_media_url(post_dict["media_url"])
            
        result.append(PostWithCounts(**post_dict))
    
    return result

def get_user_posts(db: Session, user_id: str, skip: int = 0, limit: int = 20) -> List[Post]:
    """Get posts by user ID"""
    logging.info(f"Getting posts for user ID: {user_id} with skip={skip}, limit={limit}")
    return (
        db.query(Post)
        .filter(Post.author_id == user_id)
        .order_by(Post.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def create_post(db: Session, post_in: PostCreate, author_id: str) -> Post:
    """Create new post"""
    logging.info(f"Creating post for author ID: {author_id}")
    post = Post(
        id=str(uuid.uuid4()),
        author_id=author_id,
        **post_in.dict(),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post

def update_post(db: Session, post: Post, post_in: PostUpdate) -> Post:
    """Update post"""
    logging.info(f"Updating post with ID: {post.id}")
    # Get the post from the current session to avoid session conflicts
    db_post = db.query(Post).filter(Post.id == post.id).first()
    if not db_post:
        # This should not happen, but just in case
        raise ValueError(f"Post with ID {post.id} not found in the database")
    
    update_data = post_in.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_post, field, value)
 
   
    db.commit()
    db.refresh(db_post)
    
    return db_post

def delete_post(db: Session, post: Post) -> Post:
    """
    Delete post and all associated comments and reactions
    """
    logging.info(f"Deleting post with ID: {post.id}")
    # Delete associated reactions and comments first to maintain referential integrity
    db.query(Reaction).filter(Reaction.post_id == post.id).delete()
    db.query(Comment).filter(Comment.post_id == post.id).delete()
    
    # Finally, delete the post itself
    db.delete(post)
    db.commit()
    return post 