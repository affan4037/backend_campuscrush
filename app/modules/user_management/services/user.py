from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.modules.user_management.models.user import User
from app.modules.user_management.schemas.user import UserUpdate

def get_user(db: Session, user_id: str) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Get list of users"""
    return db.query(User).offset(skip).limit(limit).all()

def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
    """Update user"""
    # Get the user from the current session to avoid session conflicts
    db_user = db.query(User).filter(User.id == user.id).first()
    if not db_user:
        # This should not happen, but just in case
        raise ValueError(f"User with ID {user.id} not found in the database")
    
    update_data = user_in.dict(exclude_unset=True)
    
    # Handle password update separately to ensure proper hashing
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data["password"])
        del update_data["password"]
    
    # Apply all updates at once
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    # No need to call db.add() since db_user is already tracked by the session
    db.commit()
    db.refresh(db_user)
    
    return db_user 