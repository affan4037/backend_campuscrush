from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func

from app.db.session import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)  # The user who triggered the notification
    type = Column(String)  # friend_request, friend_accept, post_like, post_comment, etc.
    content = Column(Text)
    related_id = Column(String, nullable=True)  # ID of the related entity (post, comment, user, etc.)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now()) 


