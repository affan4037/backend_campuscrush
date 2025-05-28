from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.modules.user_management.schemas.user import User

class NotificationBase(BaseModel):
    type: str
    content: str
    related_id: Optional[str] = None

class NotificationCreate(NotificationBase):
    user_id: str
    actor_id: Optional[str] = None  # ID of the user who triggered the notification

class NotificationUpdate(BaseModel):
    is_read: bool = True

class NotificationInDBBase(NotificationBase):
    id: str
    user_id: str
    is_read: bool
    created_at: datetime
    actor_id: Optional[str] = None  
    class Config:
        orm_mode = True

class Notification(NotificationInDBBase):
    """Notification model returned to client"""
    actor: Optional[User] = None  # User object of the actor
    post_id: Optional[str] = None  # Extracted from related_id based on type
    comment_id: Optional[str] = None  # Extracted from related_id based on type
    pass 