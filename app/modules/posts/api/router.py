from typing import Any, List
import os
import shutil
from pathlib import Path
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

# Get the logger
logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.deps import get_current_active_verified_user
from app.modules.user_management.models.user import User
from app.modules.posts.models.post import Post
from app.modules.posts.schemas.post import Post as PostSchema, PostCreate, PostUpdate, PostWithCounts

# Uncomment the actual service functions
from app.modules.posts.services.post import (
    get_post, get_posts, get_posts_with_counts, get_user_posts, 
    create_post, update_post, delete_post
)
from app.core.config import settings
from app.core.storage import r2_storage

# Create a router that explicitly disables the automatic trailing slash behavior
router = APIRouter(prefix="")

@router.get("/", response_model=List[PostWithCounts])
def read_posts(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """
    Retrieve posts with comment and reaction counts.
    """
    return get_posts_with_counts(db, skip=skip, limit=limit)

async def _handle_media_upload(media: UploadFile) -> str:
    """Process media file upload and return media URL"""
    if not media:
        return None
        
    allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov"]
    file_extension = os.path.splitext(media.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Please use one of: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Upload to R2 storage
        return await r2_storage.upload_file(media, "post_media")
    except Exception as e:
        logger.error(f"Error uploading media: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload media"
        )

@router.post("/", response_model=PostSchema)
@router.post("", response_model=PostSchema)
async def create_new_post( 
    *,
    db: Session = Depends(get_db),
    content: str = Form(...),
    media: UploadFile = File(None),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """
    Create new post with optional media file.
    """
    try:
        media_url = await _handle_media_upload(media) if media else None
        post_data = PostCreate(content=content, media_url=media_url)
        return create_post(db, post_data, current_user.id)
    except Exception as e:
        if "media" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error processing media: {str(e)}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post"
        )

@router.get("/{post_id}", response_model=PostSchema)
def read_post_by_id(
    *,
    db: Session = Depends(get_db),
    post_id: str,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """
    Get post by ID.
    """
    post = get_post(db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    return post

@router.put("/{post_id}", response_model=PostSchema)
def update_post_by_id(
    *,
    db: Session = Depends(get_db),
    post_id: str,
    post_in: PostUpdate,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """
    Update a post.
    """
    post = get_post(db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    # Check if user is the author
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return update_post(db, post, post_in)

@router.delete("/{post_id}", response_model=PostSchema)
def delete_post_by_id(
    *,
    db: Session = Depends(get_db),
    post_id: str,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """
    Delete a post and all associated data (comments and reactions).
    This is a cascading delete operation that will remove:
    1. All reactions on this post
    2. All comments on this post
    3. The post itself
    """
    post = get_post(db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    # Check if user is the author
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return delete_post(db, post)

@router.get("/user/{user_id}", response_model=List[PostSchema])
def read_user_posts_by_id(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """
    Get posts by user ID.
    """
    return get_user_posts(db, user_id=user_id, skip=skip, limit=limit)

#  Decorater is used to automate wrapping the function.
@router.get("/check-media/{media_filename}", include_in_schema=settings.DEBUG)
async def check_media_path(
    media_filename: str,
) -> Any:
    """
    Diagnostic endpoint to help troubleshoot media URLs.
    This endpoint is only available in debug mode.
    """
    # Check all potential paths where the file might exist
    base_path = Path("uploads")
    potential_paths = [
        base_path / media_filename,
        base_path / "post_media" / media_filename,
    ]
    
    results = []
    for path in potential_paths:
        exists = os.path.exists(path)
        size = None
        modified_time = None
        
        if exists:
            try:
                size = os.path.getsize(path)
                modified_time = os.path.getmtime(path)
            except Exception as e:
                logger.error(f"Error getting file info: {e}")
                
        results.append({
            "path": str(path),
            "exists": exists,
            "size": size,
            "modified": modified_time,
            "url": f"{settings.BASE_URL}{settings.API_V1_STR}/static/{path.relative_to(base_path)}"
        })
    
    # Check the 'uploads' directory structure
    uploads_dir = Path('uploads')
    dir_contents = []
    
    if uploads_dir.exists() and uploads_dir.is_dir():
        try:
            for item in uploads_dir.iterdir():
                if item.is_dir():
                    dir_contents.append({
                        "name": item.name,
                        "type": "directory",
                        "path": str(item),
                    })
                else:
                    dir_contents.append({
                        "name": item.name,
                        "type": "file",
                        "size": os.path.getsize(item),
                        "path": str(item),
                    })
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
            dir_contents = [{"error": str(e)}]
    else:
        dir_contents = [{"error": "Uploads directory not found"}]
    
    # Check post_media directory
    post_media_dir = Path('uploads/post_media')
    post_media_contents = []
    
    if post_media_dir.exists() and post_media_dir.is_dir():
        try:
            file_count = 0
            total_size = 0
            for item in post_media_dir.iterdir():
                # Limit to 10 items to avoid too much output
                if file_count < 10:
                    size = os.path.getsize(item) if item.is_file() else 0
                    post_media_contents.append({
                        "name": item.name,
                        "type": "file" if item.is_file() else "directory",
                        "size": size,
                    })
                file_count += 1
                if item.is_file():
                    total_size += size
            
            post_media_contents.append({
                "total_files": file_count,
                "total_size": total_size,
            })
        except Exception as e:
            logger.error(f"Error listing post_media directory: {e}")
            post_media_contents = [{"error": str(e)}]
    else:
        post_media_contents = [{"error": "post_media directory not found"}]
    
    # Check if the media file exists using a direct URL access
    direct_url_check = None
    try:
        # Construct URLs to test
        static_url = f"{settings.BASE_URL}{settings.API_V1_STR}/static/{media_filename}"
        post_media_url = f"{settings.BASE_URL}{settings.API_V1_STR}/static/post_media/{media_filename}"
        
        # Test the URLs using async requests
        direct_url_check = {
            "direct_static": {
                "url": static_url,
                "status": "unchecked"
            },
            "post_media": {
                "url": post_media_url,
                "status": "unchecked"
            }
        }
    except Exception as e:
        logger.error(f"Error constructing URLs: {e}")
        direct_url_check = {"error": str(e)}
    
    return {
        "filename": media_filename,
        "paths_checked": results,
        "static_mount_point": f"{settings.API_V1_STR}/static",
        "uploads_dir": str(base_path.absolute()),
        "uploads_structure": dir_contents,
        "post_media_dir": str(post_media_dir.absolute()),
        "post_media_contents": post_media_contents,
        "direct_urls": direct_url_check,
        "server_address": settings.BASE_URL,
    } 