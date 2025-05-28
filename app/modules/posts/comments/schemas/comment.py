from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.modules.user_management.schemas.user import User

class CommentBase(BaseModel):
    content: str
    parent_id: Optional[str] = None

class CommentCreate(CommentBase):
    post_id: str

class CommentUpdate(BaseModel):
    content: str

class CommentInDBBase(CommentBase):
    id: str
    author_id: str
    post_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class Comment(CommentInDBBase):
    """Comment model returned to client"""
    author: Optional[User] = None
    like_count: int = 0
    has_liked: bool = False
    replies_count: int = 0
    is_edited: bool = False

class CommentWithReplies(Comment):
    """Comment model with replies"""
    replies: List[Comment] = [] 