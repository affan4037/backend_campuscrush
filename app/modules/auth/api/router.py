"""Authentication router for Google Sign-In"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from fastapi.security import OAuth2PasswordBearer
import os

from app.core.config import settings
from app.db.session import get_db
from app.modules.auth.schemas.auth import Token, GoogleSignInRequest
from app.modules.auth.services.firebase_auth import authenticate_with_google
from app.core.security import verify_access_token, get_current_user

router = APIRouter()

@router.post("/google-signin", response_model=Token)
async def google_signin(
    *, 
    db: Session = Depends(get_db), 
    google_signin: GoogleSignInRequest
) -> Token:
    """Authenticate user with Google Sign-In"""
    success, result = authenticate_with_google(db, google_signin)
    
    if not success:
        error_msg = result.get("error", "Authentication failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "access_token": result["access_token"],
        "token_type": result["token_type"],
    }

@router.get("/validate-token", response_model=Dict[str, Any])
async def validate_token(
    db: Session = Depends(get_db),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login"))
) -> Dict[str, Any]:
    """Validate the current user's token and return user information"""
    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "valid": True,
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_verified": user.is_verified
    }

@router.get("/firebase-status", response_model=Dict[str, Any])
async def firebase_status():
    """Check Firebase configuration status (only in non-production environments)"""
    # Don't expose configuration details in production
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is not available in production"
        )
    
    # Get Firebase configuration status
    service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH', 'firebase-service-account.json')
    firebase_service_account_exists = os.environ.get('FIREBASE_SERVICE_ACCOUNT') is not None
    
    return {
        "environment": settings.ENVIRONMENT,
        "service_account_path": service_account_path,
        "service_account_file_exists": os.path.exists(service_account_path),
        "firebase_service_account_env_exists": firebase_service_account_exists,
        "firebase_initialized": True  # If the app is running, Firebase was initialized
    }  