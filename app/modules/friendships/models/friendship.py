from sqlalchemy import Column, String, DateTime, ForeignKey, Table, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base

# Create a proper Friendship class that maps to the friendships table
class Friendship(Base):
    __tablename__ = "friendships"
    
    user_id = Column(String, ForeignKey('users.id'), primary_key=True)
    friend_id = Column(String, ForeignKey('users.id'), primary_key=True)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),
        CheckConstraint('user_id != friend_id', name='no_self_friendship'),
    )

# Friend request model
class FriendshipRequest(Base):
    __tablename__ = "friendship_requests"

    id = Column(String, primary_key=True, index=True)
    sender_id = Column(String, ForeignKey("users.id"))
    receiver_id = Column(String, ForeignKey("users.id"))
    status = Column(String, default="pending")  # pending, accepted, rejected
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now()) 