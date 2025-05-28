from typing import List, Optional
import uuid
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.modules.friendships.models.friendship import Friendship, FriendshipRequest
from app.modules.friendships.schemas.friendship import FriendshipRequestCreate, FriendshipRequestUpdate
from app.modules.user_management.models.user import User
from app.modules.user_management.services.user import get_user

logger = logging.getLogger(__name__)

# Request operations
def get_friend_request(db: Session, sender_id: str, receiver_id: str) -> Optional[FriendshipRequest]:
    """Get friend request by sender and receiver IDs"""
    return db.query(FriendshipRequest).filter(
        FriendshipRequest.sender_id == sender_id,
        FriendshipRequest.receiver_id == receiver_id
    ).first()

def get_friend_request_by_id(db: Session, request_id: str) -> Optional[FriendshipRequest]:
    """Get friend request by ID"""
    return db.query(FriendshipRequest).filter(FriendshipRequest.id == request_id).first()

def get_friend_requests(db: Session, user_id: str, direction: str = "received", status: Optional[str] = None) -> List[FriendshipRequest]:
    """Get friend requests for a user with specified direction and status"""
    if direction not in ["sent", "received"]:
        logger.warning(f"Invalid direction '{direction}' specified in get_friend_requests")
        return []
    
    # Build query based on direction
    field = FriendshipRequest.receiver_id if direction == "received" else FriendshipRequest.sender_id
    query = db.query(FriendshipRequest).filter(field == user_id)
    
    if status is not None:
        query = query.filter(FriendshipRequest.status == status)
    return query.all()

def get_received_friend_requests(db: Session, user_id: str, status: Optional[str] = None) -> List[FriendshipRequest]:
    """Get received friend requests for a user"""
    return get_friend_requests(db, user_id, "received", status)

def get_sent_friend_requests(db: Session, user_id: str, status: Optional[str] = None) -> List[FriendshipRequest]:
    """Get sent friend requests by a user"""
    return get_friend_requests(db, user_id, "sent", status)

def create_friend_request(db: Session, request_in: FriendshipRequestCreate, sender_id: str) -> FriendshipRequest:
    """Create a new friend request"""
    receiver_id = request_in.receiver_id
    
    # Check for existing requests
    existing_request = get_friend_request(db, sender_id, receiver_id)
    if existing_request:
        return existing_request
    
    # Check for reverse direction request
    reverse_request = get_friend_request(db, receiver_id, sender_id)
    if reverse_request:
        # If the receiver already sent a request, accept it
        reverse_request.status = "accepted"
        db.add(reverse_request)
        
        # Create the friendship for both users
        create_friendship(db, sender_id, receiver_id)
        
        db.commit()
        db.refresh(reverse_request)
        return reverse_request
    
    # Create new request
    friend_request = FriendshipRequest(
        id=str(uuid.uuid4()),
        sender_id=sender_id,
        receiver_id=receiver_id,
        status="pending"
    )
    
    db.add(friend_request)
    db.commit()
    db.refresh(friend_request)
    return friend_request

def update_friend_request(db: Session, friend_request: FriendshipRequest, request_in: FriendshipRequestUpdate) -> FriendshipRequest:
    """Update a friend request"""
    friend_request.status = request_in.status
    
    # If accepted, create friendship
    if request_in.status == "accepted":
        create_friendship(db, friend_request.sender_id, friend_request.receiver_id)
    
    db.add(friend_request)
    db.commit()
    db.refresh(friend_request)
    return friend_request

def delete_friend_request(db: Session, friend_request: FriendshipRequest) -> FriendshipRequest:
    """Delete a friend request"""
    db.delete(friend_request)
    db.commit()
    return friend_request

# Friendship operations
def get_bidirectional_friendship_filter(user_id: str, friend_id: str):
    """Create a filter for bidirectional friendship between two users"""
    return or_(
        and_(Friendship.user_id == user_id, Friendship.friend_id == friend_id),
        and_(Friendship.user_id == friend_id, Friendship.friend_id == user_id)
    )

def get_friendship(db: Session, user_id: str, friend_id: str) -> Optional[Friendship]:
    """Get a friendship between two users"""
    return db.query(Friendship).filter(
        get_bidirectional_friendship_filter(user_id, friend_id)
    ).first()

def check_friendship(db: Session, user_id: str, friend_id: str) -> bool:
    """Check if two users are friends"""
    return get_friendship(db, user_id, friend_id) is not None

def create_friendship(db: Session, user_id: str, friend_id: str) -> bool:
    """Create a bidirectional friendship between two users"""
    # Check if friendship already exists
    if get_friendship(db, user_id, friend_id):
        return False

    try:
        with db.begin():
            # Create both friendship directions
            db.add(Friendship(user_id=user_id, friend_id=friend_id))
            db.add(Friendship(user_id=friend_id, friend_id=user_id))
        logger.info(f"Successfully created bidirectional friendship: {user_id} <-> {friend_id}")
        return True
    except Exception as e:
        # The with db.begin() block handles rollback automatically on exception
        logger.error(f"Error creating friendship: {e}")
        return False

def remove_friendship(db: Session, user_id: str, friend_id: str) -> bool:
    """Remove a bidirectional friendship between two users"""
    try:
        with db.begin():
            # Remove friendship (both ways)
            db.query(Friendship).filter(
                get_bidirectional_friendship_filter(user_id, friend_id)
            ).delete(synchronize_session=False)

            # Remove any related friend requests
            db.query(FriendshipRequest).filter(
                or_(
                    and_(FriendshipRequest.sender_id == user_id, FriendshipRequest.receiver_id == friend_id),
                    and_(FriendshipRequest.sender_id == friend_id, FriendshipRequest.receiver_id == user_id)
                )
            ).delete(synchronize_session=False)
        logger.info(f"Successfully removed bidirectional friendship: {user_id} <-> {friend_id}")
        return True
    except Exception as e:
        # The with db.begin() block handles rollback automatically on exception
        logger.error(f"Error removing friendship: {e}")
        return False

def get_friends(db: Session, user_id: str) -> List[User]:
    """Get a user's friends (as User objects)"""
    try:
        # Query all friends in one step by combining both directions
        friend_query = db.query(
            Friendship.friend_id if Friendship.user_id == user_id else Friendship.user_id
        ).filter(
            or_(
                Friendship.user_id == user_id,
                Friendship.friend_id == user_id
            )
        )
        
        # Get unique friend IDs
        all_friend_ids = {
            friend_id[0] for friend_id in friend_query.all()
            if friend_id[0] != user_id
        }
        
        # Get user objects for all friend IDs
        friends = []
        for friend_id in all_friend_ids:
            friend = get_user(db, friend_id)
            if friend:
                friends.append(friend)
            else:
                logger.warning(f"Friend relationship exists but user not found: {friend_id}")
        
        return friends
    except Exception as e:
        logger.error(f"Error getting friends for user {user_id}: {e}")
        return [] 
    

