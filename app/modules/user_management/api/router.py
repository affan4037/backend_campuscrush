from typing import Any, List, Optional
import os
import shutil
from pathlib import Path
import logging
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user, get_current_active_verified_user
from app.modules.user_management.models.user import User
from app.modules.user_management.schemas.user import User as UserSchema, UserUpdate
from app.modules.user_management.services.user import get_users, get_user_by_username, update_user, get_user
from app.core.config import settings
from app.modules.posts.schemas.post import Post as PostSchema
from app.modules.friendships.services.friendship import get_friends, check_friendship, get_friend_requests
from app.modules.friendships.models.friendship import Friendship
from app.core.storage import r2_storage
from app.modules.posts.services.post import get_user_posts



router = APIRouter()
logger = logging.getLogger("app")

def _validate_user(db: Session, user_id: str) -> User:
    """Validate user exists and return user object or raise HTTPException"""
    user = get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user

def _convert_user_to_schema(user: User) -> UserSchema:
    """Convert User model to UserSchema. """
    return UserSchema.from_orm(user)

@router.get("/me", response_model=UserSchema)
def read_user_me(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get current user"""
    return current_user

@router.put("/me", response_model=UserSchema)
def update_user_me(
    *,
    db: Session = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update current user"""
    return update_user(db, current_user, user_in)

@router.get("/by-username/{username}", response_model=UserSchema)
def read_user_by_username(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Get a specific user by username"""
    user = get_user_by_username(db, username=username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.get("/search", response_model=List[UserSchema])
def search_users(
    *,
    db: Session = Depends(get_db),
    q: str = Query(..., min_length=2, description="Search query for name or username"),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Search for users by name or username"""
    search_terms = q.lower().split()
    query = db.query(User)
    
    for term in search_terms:
        search_pattern = f"%{term}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern),
            )
        )
    
    # Filter and limit results
    users = query.filter(
        User.id != current_user.id,
        User.is_verified == True
    ).limit(20).all()
    
    results = []
    for user in users:

        user_dict = user.__dict__.copy()
        if "_sa_instance_state" in user_dict:
            user_dict.pop("_sa_instance_state")
        user_schema = UserSchema(**user_dict)
            
        results.append(user_schema)
    
    return results

@router.post("/profile-picture", response_model=dict)
async def upload_profile_picture(
    *,
    db: Session = Depends(get_db),
    profile_picture: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Upload a profile picture for the current user"""
    allowed_extensions = [".jpg", ".jpeg", ".png"]
    file_extension = os.path.splitext(profile_picture.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Please use one of: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Upload to R2 storage with the user's ID as part of the filename
        # This ensures we can easily identify which user the profile picture belongs to
        original_filename = profile_picture.filename
        profile_picture.filename = f"{current_user.id}{file_extension}"
        
        # Whether we successfully used R2
        used_r2 = False
        profile_picture_url = None
        
        # Try R2 upload first
        if r2_storage.client:
            try:
                # Upload to R2 with profile_pictures prefix
                profile_picture_url = await r2_storage.upload_file(
                    profile_picture, 
                    prefix="profile_pictures"
                )
                used_r2 = True
                logger.info(f"Uploaded profile picture to R2: {profile_picture_url}")
            except Exception as r2_error:
                logger.error(f"Failed to upload to R2: {r2_error}")
        else:
            logger.warning("R2 storage not configured")
        
        # If R2 upload fails or not configured, fall back to local storage
        if not used_r2:
            logger.warning("Falling back to local storage for profile picture")
            upload_dir = Path("uploads/profile_pictures")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            unique_filename = f"{current_user.id}{file_extension}"
            file_path = upload_dir / unique_filename
            
            with open(file_path, "wb") as buffer:
                await profile_picture.seek(0)
                shutil.copyfileobj(profile_picture.file, buffer)
            
            # Use Railway URL if in production
            base_url = settings.BASE_URL
            profile_picture_url = f"{base_url}{settings.API_V1_STR}/static/profile_pictures/{unique_filename}"
            logger.info(f"Generated local storage URL: {profile_picture_url}")
        
        # Update user's profile picture in database
        update_user(db, current_user, UserUpdate(profile_picture=profile_picture_url))
        
        storage_type = "Cloudflare R2" if used_r2 else "local storage"
        return {
            "message": f"Profile picture uploaded successfully using {storage_type}",
            "profile_picture_url": profile_picture_url,
            "storage_type": storage_type
        }
    except Exception as e:
        logger.error(f"Error uploading profile picture: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload profile picture: {e}"
        )

@router.get("/suggestions", response_model=dict)
def get_suggested_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    exclude_friends: bool = Query(True, description="Whether to exclude friends from suggestions"),
    status: Optional[str] = Query(None, description="Filter by relationship status (not_friends)"),
    debug: bool = Query(False, description="Enable extra debugging information"),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Get suggested users for "People You May Know" feature"""
    # Fix one-way friendships if any exist
    _fix_one_way_friendships(db)
    
    # Get all friend IDs using multiple methods for reliability
    all_friend_ids = _get_all_friend_ids(db, current_user.id, debug)
    
    # Get pending friend requests
    pending_user_ids = _get_pending_request_user_ids(db, current_user.id)
    
    # Get all verified users 
    all_users = get_users(db, skip=skip, limit=limit)
    
    # Filter and process users
    user_schemas = []
    excluded_friends = 0
    excluded_pending = 0
    
    for user in all_users:
        # Skip current user
        if user.id == current_user.id:
            continue
                
        # Check if user is a friend (multiple checks for reliability)
        is_friend = _is_user_friend(db, current_user.id, user.id, all_friend_ids)
        
        if is_friend:
            excluded_friends += 1
            continue
                
        # Check if this is a pending connection
        if user.id in pending_user_ids:
            excluded_pending += 1
            continue
                
        # Only include verified users
        if not user.is_verified:
            continue
                
        # Limit to requested number
        if len(user_schemas) >= limit:
            break
        
        # Convert user to schema
        user_schema = _convert_user_to_schema(user)
        
        # Generate fallback avatar if needed
        if not user_schema.profile_picture:
            name = urllib.parse.quote(user_schema.full_name)
            user_schema.profile_picture = f"https://ui-avatars.com/api/?name={name}&background=random&color=fff&size=256"
        
        user_schemas.append(user_schema)
    
    return {
        "items": user_schemas,
        "total": len(user_schemas),
        "limit": limit,
        "skip": skip,
    }

def _fix_one_way_friendships(db: Session) -> None:
    """Fix any one-way friendships by creating the missing reverse entries"""
    with db.begin():
        all_friendships = db.query(Friendship).all()
        friendship_pairs = set()
        for f in all_friendships:
            friendship_pairs.add((f.user_id, f.friend_id))
        
        # Check for one-way friendships
        problematic_friendships = []
        for user_id, friend_id in friendship_pairs:
            if (friend_id, user_id) not in friendship_pairs:
                problematic_friendships.append((user_id, friend_id))
                # Create missing reverse friendship
                try:
                    logger.warning(f"Creating missing friendship record: {friend_id} -> {user_id}")
                    db.add(Friendship(user_id=friend_id, friend_id=user_id))
                except Exception as e:
                    logger.error(f"Failed to create reverse friendship: {e}")
        
        # Only commit if we made changes
        if problematic_friendships:
            logger.warning(f"Fixed {len(problematic_friendships)} one-way friendships")

def _get_all_friend_ids(db: Session, user_id: str, debug: bool = False) -> set:
    """Get comprehensive set of friend IDs using multiple methods"""
    # Method 1: Get user's friends via get_friends function 
    friends_from_function = get_friends(db, user_id)
    friend_ids_from_function = {friend.id for friend in friends_from_function}
    logger.debug(f"Method 1: Found {len(friend_ids_from_function)} friends via get_friends function")
    
    # Method 2: Direct database query for friendship records 
    direct_friendships = db.query(Friendship).filter(
        or_(
            Friendship.user_id == user_id,
            Friendship.friend_id == user_id
        )
    ).all()
    
    direct_friend_ids = set()
    for f in direct_friendships:
        if f.user_id == user_id:
            direct_friend_ids.add(f.friend_id)
        else:
            direct_friend_ids.add(f.user_id)
    
    logger.debug(f"Method 2: Found {len(direct_friend_ids)} friends via direct query")
    
    # Method 3: Check each user individually via check_friendship (only in debug mode)
    manually_checked_friend_ids = set()
    if debug:
        all_possible_users = get_users(db, skip=0, limit=1000)
        for user in all_possible_users:
            if user.id != user_id and check_friendship(db, user_id, user.id):
                manually_checked_friend_ids.add(user.id)
        logger.debug(f"Method 3: Found {len(manually_checked_friend_ids)} friends via manual check")
    
    # Combine all methods for a comprehensive friend list
    all_friend_ids = friend_ids_from_function | direct_friend_ids | manually_checked_friend_ids
    
    # Log any discrepancies for debugging
    missing_from_function = direct_friend_ids - friend_ids_from_function
    if missing_from_function:
        logger.warning(f"CRITICAL: {len(missing_from_function)} friends missing from get_friends result")
        for fid in missing_from_function:
            logger.warning(f"Missing friend in get_friends: {fid}")
            
    return all_friend_ids

def _is_user_friend(db: Session, user_id: str, other_user_id: str, friend_ids: set = None) -> bool:
    """Check if two users are friends, using precomputed friend_ids if available"""
    if friend_ids is not None:
        return other_user_id in friend_ids
    return check_friendship(db, user_id, other_user_id)

def _get_pending_request_user_ids(db: Session, user_id: str) -> set:
    """Get IDs of users with pending friend requests"""
    
    # Get pending friend requests - both sent and received
    sent_requests = get_friend_requests(db, user_id, direction="sent")
    received_requests = get_friend_requests(db, user_id, direction="received")
    
    pending_user_ids = set()
    for req in sent_requests + received_requests:
        try:
            # Handle sender_id
            if req.sender_id and req.sender_id != user_id:
                pending_user_ids.add(req.sender_id)
            
            # Handle receiver_id
            if hasattr(req, 'receiver_id') and req.receiver_id and req.receiver_id != user_id:
                pending_user_ids.add(req.receiver_id)
        except Exception as e:
            logger.warning(f"Error processing request {req.id if hasattr(req, 'id') else 'unknown'}: {e}")
    
    logger.debug(f"Found {len(pending_user_ids)} pending connections to exclude")
    
    return pending_user_ids

@router.get("", response_model=List[UserSchema])
def read_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=50),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Retrieve users with pagination"""
    return get_users(db, skip=skip, limit=limit)

@router.get("/{user_id}", response_model=UserSchema)
def read_user_by_id(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Get a specific user by id"""
    return _validate_user(db, user_id)

@router.get("/{user_id}/posts", response_model=List[PostSchema])
def read_user_owned_posts(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Get posts created by a specific user"""
    _validate_user(db, user_id)
    
    
    return get_user_posts(db, user_id=user_id, skip=skip, limit=limit) 