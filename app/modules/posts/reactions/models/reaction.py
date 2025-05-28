from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.db.session import Base

class Reaction(Base):
    __tablename__ = "reactions"

    id = Column(String, primary_key=True, index=True)
    reaction_type = Column(String)  # like, love, haha, wow, sad, angry
    user_id = Column(String, ForeignKey("users.id"))
    post_id = Column(String, ForeignKey("posts.id"))
    created_at = Column(DateTime, default=func.now()) 