from typing import List, Set
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

from app.modules.posts.models.post import Post as PostModel
from app.modules.user_management.models.user import User as UserModel
from app.modules.posts.comments.models.comment import Comment
from app.modules.posts.reactions.models.reaction import Reaction
from app.modules.friendships.models.friendship import Friendship
from app.modules.home_feed.schemas.feed import FeedItem, FeedResponse
from app.modules.posts.schemas.post import Post as PostSchema
from app.modules.user_management.schemas.user import User as UserSchema

def get_home_feed(db: Session, user_id: str, skip: int = 0, limit: int = 20) -> FeedResponse:
    friend_ids = _get_friend_ids(db, user_id)
    author_ids = friend_ids + [user_id]
    
    # Build main query with all necessary data
    query = _build_feed_query(db, author_ids)
    
    # Get counts and paginate results
    total = query.count()
    posts = query.offset(skip).limit(limit).all()
    
    # Transform database results to response objects
    feed_items = [
        _create_feed_item(db, post_data, user_id) 
        for post_data in posts
    ]
    
    return FeedResponse(
        items=feed_items,
        total=total,
        has_more=total > skip + limit
    )

def _get_friend_ids(db: Session, user_id: str) -> List[str]:
    """Get all friend IDs from both friendship directions"""
    try:
        # Query both directions of friendship in a single query
        friendship_query = db.query(
            func.coalesce(Friendship.friend_id, Friendship.user_id).label('friend_id')
        ).filter(
            or_(
                Friendship.user_id == user_id,
                Friendship.friend_id == user_id
            )
        )
        
        # Extract unique friend IDs, excluding the user's own ID
        friend_ids = {
            row.friend_id for row in friendship_query.all() 
            if row.friend_id != user_id
        }
        
        return list(friend_ids)
    except Exception as e:
        # Handle case where friendship table doesn't exist yet
        if "relation \"friendships\" does not exist" in str(e):
            return []
        raise

def _build_feed_query(db: Session, author_ids: List[str]):
    """Build optimized query for fetching feed posts with metrics"""
    return (
        db.query(
            PostModel,
            UserModel,
            func.count(Comment.id).label("comment_count"),
            func.count(Reaction.id).label("reaction_count")
        )
        .join(UserModel, UserModel.id == PostModel.author_id)
        .outerjoin(Comment, Comment.post_id == PostModel.id)
        .outerjoin(Reaction, Reaction.post_id == PostModel.id)
        .filter(PostModel.author_id.in_(author_ids))
        .group_by(PostModel.id, UserModel.id)
        .order_by(desc(PostModel.created_at))
    )

def _create_feed_item(db: Session, post_data, user_id: str) -> FeedItem:
    """Transform raw query results into a structured feed item"""
    post_model, author_model, comment_count, reaction_count = post_data
     
    #  user_reaction variable is a Reaction object if the user has reacted to the post, otherwise it is None.
    # Check if user has reacted to this post
    user_reaction = db.query(Reaction).filter(
        Reaction.post_id == post_model.id,
        Reaction.user_id == user_id
    ).first()
    # Create schema objects from models
    post = _create_post_schema(post_model)
    author = _create_user_schema(author_model)
    
    return FeedItem(
        post=post,
        author=author,
        comment_count=comment_count,
        reaction_count=reaction_count,
        has_reacted=user_reaction is not None,
        reaction_type=user_reaction.reaction_type if user_reaction else None
    )

def _create_post_schema(post_model: PostModel) -> PostSchema:
    """Create a post schema object from a post model"""
    return PostSchema(
        id=post_model.id,
        content=post_model.content,
        media_url=post_model.media_url,
        author_id=post_model.author_id,
        created_at=post_model.created_at,
        updated_at=post_model.updated_at
    )

def _create_user_schema(user_model: UserModel) -> UserSchema:
    """Create a user schema object from a user model"""
    return UserSchema(
        id=user_model.id,
        email=user_model.email,
        username=user_model.username,
        full_name=user_model.full_name,
        university=user_model.university,
        is_active=user_model.is_active,
        is_verified=user_model.is_verified,
        created_at=user_model.created_at,
        updated_at=user_model.updated_at,
        profile_picture=user_model.profile_picture
    ) 