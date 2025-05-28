from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, validator

class FriendshipRequestBase(BaseModel):
    receiver_id: str

class FriendshipRequestCreate(FriendshipRequestBase):
    pass

class FriendshipRequestUpdate(BaseModel):
    status: str
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ["accepted", "rejected"]
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v

class FriendshipRequestInDBBase(FriendshipRequestBase):
    id: str
    sender_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class FriendshipRequest(FriendshipRequestInDBBase):
    """Friend request model returned to client"""
    pass

class FriendshipBase(BaseModel):
    user_id: str
    friend_id: str

class FriendshipInDBBase(FriendshipBase):
    user_id: str
    
    class Config:
        orm_mode = True

class Friendship(FriendshipInDBBase):
    """Friendship model returned to client"""
    pass 