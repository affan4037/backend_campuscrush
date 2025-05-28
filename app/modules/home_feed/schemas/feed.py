from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.modules.posts.schemas.post import Post
from app.modules.user_management.schemas.user import User

class FeedItem(BaseModel):
    """Feed item model returned to client"""
    post: Post
    author: User
    comment_count: int
    reaction_count: int
    has_reacted: bool
    reaction_type: Optional[str] = None

class FeedResponse(BaseModel):
    """Feed response model returned to client"""
    items: List[FeedItem]
    total: int
    has_more: bool 