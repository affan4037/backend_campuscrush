from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_active_verified_user, get_current_user
from app.modules.user_management.models.user import User
from app.modules.notifications.models.notification import Notification
from app.modules.notifications.schemas.notification import (
    Notification as NotificationSchema,
    NotificationUpdate
)
from services.notification import (
    get_notification,
    get_user_notifications,
    update_notification,
    mark_all_as_read,
    delete_notification,
    delete_all_notifications
)

router = APIRouter()

@router.get("", response_model=List[NotificationSchema])
@router.get("/", response_model=List[NotificationSchema])
def read_notifications(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get user's notifications with pagination and filter options"""
    return get_user_notifications(db, current_user.id, skip, limit, unread_only)

@router.put("/{notification_id}", response_model=NotificationSchema)
def mark_notification_as_read(
    *,
    db: Session = Depends(get_db),
    notification_id: str,
    notification_in: NotificationUpdate,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Mark a specific notification as read"""
    notification = get_notification(db, notification_id=notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return update_notification(db, notification, notification_in)

@router.put("/mark-all-read", response_model=dict)
def mark_all_notifications_as_read(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Mark all of the user's notifications as read"""
    count = mark_all_as_read(db, current_user.id)
    
    return {
        "message": f"Marked {count} notifications as read",
        "count": count
    }

@router.delete("/{notification_id}", response_model=NotificationSchema)
def delete_notification_by_id(
    *,
    db: Session = Depends(get_db),
    notification_id: str,
    current_user: User = Depends(get_current_active_verified_user),
) -> Any:
    """Delete a specific notification"""
    notification = get_notification(db, notification_id=notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return delete_notification(db, notification)

@router.delete("", response_model=dict)
@router.delete("/", response_model=dict)
def delete_all_user_notifications(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Delete all notifications for the current user"""
    count = delete_all_notifications(db, current_user.id)
    
    return {
        "message": f"Deleted {count} notifications",
        "count": count
    } 