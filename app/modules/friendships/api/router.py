from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.deps import get_current_active_verified_user
from app.modules.user_management.models.user import User
from app.modules.user_management.schemas.user import User as UserSchema
from app.modules.user_management.services.user import get_user
from app.modules.friendships.schemas.friendship import (
    FriendshipRequest as FriendshipRequestSchema,
    FriendshipRequestCreate,
    FriendshipRequestUpdate
)
from app.modules.friendships.services.friendship import (
    get_friend_request,
    get_friend_request_by_id,
    get_received_friend_requests,
    get_sent_friend_requests,
    create_friend_request,
    update_friend_request,
    delete_friend_request,
    check_friendship,
    get_friends,
    remove_friendship
)
from app.modules.notifications.services.notification_events import (
    create_friend_request_notification,
    create_friend_request_accepted_notification
)

router = APIRouter()
logger = logging.getLogger(__name__)

def _check_user_exists(db: Session, user_id: str) -> None:
    """Validate user exists, raise HTTP 404 if not"""
    user = get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

def _validate_friend_request(db: Session, request_id: str, current_user_id: str, check_sender: bool = False) -> Any:
    """Validate friend request exists and user has permission to access it"""
    friend_request = get_friend_request_by_id(db, request_id=request_id)
    if not friend_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found"
        )
    
    # Check if current user is the appropriate party (sender or receiver)
    field_to_check = "sender_id" if check_sender else "receiver_id"
    if getattr(friend_request, field_to_check) != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return friend_request

@router.post("/request", response_model=FriendshipRequestSchema)
def send_friend_request(
    *,
    db: Session = Depends(get_db),
    request_in: FriendshipRequestCreate,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    receiver_id = request_in.receiver_id
    current_user_id = current_user.id
    
    # Validate receiver exists
    _check_user_exists(db, receiver_id)
    
    # Validate request is valid
    if current_user_id == receiver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send friend request to yourself"
        )
    
    if check_friendship(db, current_user_id, receiver_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already friends with this user"
        )
    
    existing_request = get_friend_request(db, current_user_id, receiver_id)
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Friend request already sent"
        )
    
    reverse_request = get_friend_request(db, receiver_id, current_user_id)
    if reverse_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user has already sent you a friend request"
        )
    
    # Create the request
    friend_request = create_friend_request(db, request_in, current_user_id)
    
    # Send notification (non-blocking)
    try:
        create_friend_request_notification(
            db=db,
            sender_id=current_user_id,
            receiver_id=receiver_id,
            request_id=friend_request.id
        )
    except Exception as e:
        logger.error(f"Error creating friend request notification: {e}")
    
    return friend_request

@router.put("/request/{request_id}", response_model=FriendshipRequestSchema)
def respond_to_friend_request(
    *,
    db: Session = Depends(get_db),
    request_id: str,
    request_in: FriendshipRequestUpdate,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    # Validate request exists and user has permission
    friend_request = _validate_friend_request(db, request_id, current_user.id)
    
    # Check if request is pending
    if friend_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Friend request already {friend_request.status}"
        )
    
    # Update the request
    updated_request = update_friend_request(db, friend_request, request_in)
    
    # Send notification for accepted requests
    if request_in.status == "accepted":
        try:
            create_friend_request_accepted_notification(
                db=db,
                accepter_id=current_user.id,
                requester_id=friend_request.sender_id
            )
        except Exception as e:
            logger.error(f"Error creating acceptance notification: {e}")
    
    return updated_request

@router.get("/requests/received", response_model=List[FriendshipRequestSchema])
def get_my_received_friend_requests(
    *,
    db: Session = Depends(get_db),
    status: str = "pending",
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    return get_received_friend_requests(db, current_user.id, status)

@router.get("/requests/sent", response_model=List[FriendshipRequestSchema])
def get_my_sent_friend_requests(
    *,
    db: Session = Depends(get_db),
    status: str = None,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    return get_sent_friend_requests(db, current_user.id, status)

@router.delete("/request/{request_id}", response_model=FriendshipRequestSchema)
def cancel_friend_request(
    *,
    db: Session = Depends(get_db),
    request_id: str,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    # Validate request exists and user has permission
    friend_request = _validate_friend_request(db, request_id, current_user.id, check_sender=True)
    return delete_friend_request(db, friend_request)

@router.get("/", response_model=List[UserSchema])
def get_my_friends(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    return get_friends(db, current_user.id)

@router.delete("/{friend_id}", response_model=Dict[str, str])
def remove_friend(
    *,
    db: Session = Depends(get_db),
    friend_id: str,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    # Validate friend exists
    _check_user_exists(db, friend_id)
    
    # Check if they are friends
    if not check_friendship(db, current_user.id, friend_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not friends with this user"
        )
    
    # Remove friendship
    remove_friendship(db, current_user.id, friend_id)
    return {"message": "Friend removed successfully"}

@router.get("/status/{user_id}", response_model=Dict[str, Any])
def check_friendship_status(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    # Validate user exists
    _check_user_exists(db, user_id)
    current_user_id = current_user.id
    
    # Check if it's the same user
    if current_user_id == user_id:
        return {"status": "self", "request_id": None}
    
    # Check if friends
    if check_friendship(db, current_user_id, user_id):
        return {"status": "friends", "request_id": None}
    
    # Check for sent request
    sent_request = get_friend_request(db, current_user_id, user_id)
    if sent_request:
        return {"status": "request_sent", "request_id": sent_request.id}
    
    # Check for received request
    received_request = get_friend_request(db, user_id, current_user_id)
    if received_request:
        return {"status": "request_received", "request_id": received_request.id}
    
    # Default - not friends
    return {"status": "not_friends", "request_id": None} 