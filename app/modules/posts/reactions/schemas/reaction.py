from typing import Optional
from datetime import datetime
from pydantic import BaseModel, validator

class ReactionBase(BaseModel):
    reaction_type: str  # like, love, haha, wow, sad, angry

    @validator('reaction_type')
    def validate_reaction_type(cls, v):
        allowed_types = ["like", "love", "haha", "wow", "sad", "angry"]
        if v not in allowed_types:
            raise ValueError(f"Reaction type must be one of: {', '.join(allowed_types)}")
        return v

class ReactionCreate(ReactionBase):
    post_id: str

class ReactionInDBBase(ReactionBase):
    id: str
    user_id: str
    post_id: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class Reaction(ReactionInDBBase):
    """Reaction model returned to client"""
    pass

class ReactionCount(BaseModel):
    """Count of reactions by type"""
    reaction_type: str
    count: int 