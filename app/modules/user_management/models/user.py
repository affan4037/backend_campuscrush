from sqlalchemy import Boolean, Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String, nullable=True)  # Now nullable since using Google auth
    bio = Column(Text, nullable=True)
    profile_picture = Column(String, nullable=True)
    university = Column(String)
    department = Column(String, nullable=True)
    graduation_year = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)  # Separate flag for email verification
    is_admin = Column(Boolean, default=False)  # Flag for system administrators
    auth_provider = Column(String, default="google")  # Changed default to 'google'
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now()) 










    