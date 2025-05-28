from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class PostBase(BaseModel):
    content: str
    media_url: Optional[str] = None

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    content: Optional[str] = None
    media_url: Optional[str] = None

class PostInDBBase(PostBase):
    id: str
    author_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class Post(PostInDBBase):
    """Post model returned to client"""
    pass

class PostWithCounts(PostInDBBase):
    """Post model with comment and reaction counts"""
    comment_count: int = 0
    reaction_count: int = 0 

    