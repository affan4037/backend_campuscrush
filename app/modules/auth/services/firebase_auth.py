"""Firebase authentication service for Google Sign-In"""
import logging
import uuid
import os
import time
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

import firebase_admin
from firebase_admin import credentials, auth

from app.core.security import get_password_hash, create_access_token
from app.modules.user_management.models.user import User
from app.modules.auth.schemas.auth import GoogleSignInRequest
from app.core.config import settings

logger = logging.getLogger("app")

# Firebase initialization state
_firebase_initialized = False
_firebase_init_attempts = 0
_firebase_max_attempts = 3
_firebase_retry_delay = 2  # seconds

def initialize_firebase():
    """Initialize Firebase with retry mechanism"""
    global _firebase_initialized, _firebase_init_attempts
    
    if _firebase_initialized:
        return True
        
    if _firebase_init_attempts >= _firebase_max_attempts:
        logger.error(f"Failed to initialize Firebase after {_firebase_max_attempts} attempts")
        return False
        
    _firebase_init_attempts += 1
    
    try:
        service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH', 'firebase-service-account.json')
        
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase initialized with service account from {service_account_path}")
        else:
            firebase_admin.initialize_app()
            logger.warning("Firebase initialized without explicit credentials")
            
        _firebase_initialized = True
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase (attempt {_firebase_init_attempts}): {e}")
        time.sleep(_firebase_retry_delay)
        return False

# Try to initialize Firebase on module load
initialize_firebase()

def verify_firebase_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Verifies Firebase ID token and extracts user data"""
    # Ensure Firebase is initialized
    if not _firebase_initialized and not initialize_firebase():
        logger.error("Cannot verify token: Firebase not initialized")
        return False, None
        
    try:
        # Log token length for debugging
        logger.info(f"Verifying Firebase token, length: {len(token) if token else 0}")
        
        # Development mode test token
        if settings.ENVIRONMENT == "development" and token == "test_firebase_token":
            logger.warning("DEVELOPMENT MODE: Using test Firebase token")
            return True, {
                "uid": "test_user_id",
                "email": "test@example.com",
                "email_verified": True,
                "name": "Test User",
                "picture": None
            }
            
        # Verify real token
        logger.debug(f"Environment: {settings.ENVIRONMENT}")
        logger.debug(f"Firebase verification attempt starting")
        decoded_token = auth.verify_id_token(token)
        logger.info(f"Firebase token verified successfully for user: {decoded_token.get('email')}")
        
        return True, {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False),
            "name": decoded_token.get("name"),
            "picture": decoded_token.get("picture")
        }
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        if hasattr(e, "detail"):
            logger.error(f"Error detail: {e.detail}")
        if settings.ENVIRONMENT == "production":
            # Log more detail in production to help diagnose issues
            logger.error(f"Token verification error details - token length: {len(token) if token else 0}")
        return False, None

def _update_existing_user(db: Session, user: User, google_data: Dict[str, Any]) -> User:
    """Updates existing user with Google data if needed"""
    updated = False
    
    if user.auth_provider != "google":
        user.auth_provider = "google"
        updated = True
            
    if google_data.get("picture") and not user.profile_picture:
        user.profile_picture = google_data.get("picture")
        updated = True
    
    if updated:
        db.commit()
        db.refresh(user)
        
    return user

def _generate_unique_username(db: Session, email: str) -> str:
    """Generates a unique username based on email"""
    username = email.split("@")[0]
    base_username = username
    suffix = 1
    
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{suffix}"
        suffix += 1
        
    return username

def get_or_create_user_from_google(db: Session, google_data: Dict[str, Any]) -> Tuple[User, bool]:
    """Gets or creates a user based on Google authentication data"""
    email = google_data.get("email")
    if not email:
        raise ValueError("Email is required for Google authentication")
        
    # Try to find existing user
    user = db.query(User).filter(User.email == email).first()
    if user:
        return _update_existing_user(db, user, google_data), False
        
    # Create new user
    username = _generate_unique_username(db, email)
    
    new_user = User(
        id=str(uuid.uuid4()),
        email=email,
        username=username,
        full_name=google_data.get("name", "Google User"),
        hashed_password=get_password_hash(uuid.uuid4().hex),
        university="Not specified",
        department=None, 
        graduation_year=None,
        is_active=True,
        is_verified=True,
        is_email_verified=True,
        profile_picture=google_data.get("picture"),
        auth_provider="google"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user, True

def authenticate_with_google(db: Session, google_signin: GoogleSignInRequest) -> Tuple[bool, Dict[str, Any]]:
    """Authenticates a user with Google Sign-In credentials"""
    try:
        # Special case for development environment with Firebase issues
        if settings.ENVIRONMENT == "development" and not _firebase_initialized:
            if google_signin.email:
                # In development, allow direct login with provided email if Firebase fails
                logger.warning("DEVELOPMENT MODE: Using email from request without Firebase verification")
                google_data = {
                    "uid": f"dev_{uuid.uuid4().hex[:8]}",
                    "email": google_signin.email,
                    "email_verified": True,
                    "name": google_signin.name or "Development User",
                    "picture": google_signin.photo_url
                }
                user, is_new_user = get_or_create_user_from_google(db, google_data)
                
                refresh_mode = google_signin.refresh
                access_token = create_access_token(
                    user.id, 
                    expires_delta=None if not refresh_mode else settings.ACCESS_TOKEN_EXPIRE_MINUTES
                )
                
                return True, {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user_id": user.id,
                    "is_new_user": is_new_user
                }
        
        # Standard flow - verify token
        success, google_data = verify_firebase_token(google_signin.firebase_token)
        
        if not success or not google_data:
            logger.error("Firebase token verification failed")
            return False, {"error": "Invalid Firebase token"}
            
        # Validate email consistency
        request_email = google_signin.email
        token_email = google_data.get("email")
        
        logger.info(f"Firebase token contains email: {token_email}")
        
        if request_email and token_email and request_email != token_email:
            logger.warning(f"Email mismatch: {request_email} vs {token_email}")
            return False, {"error": "Email mismatch between request and token"}
            
        # Get or create user
        logger.info(f"Getting or creating user for email: {token_email}")
        user, is_new_user = get_or_create_user_from_google(db, google_data)
        
        # Generate auth token - use shorter expiry for refreshes to improve security
        refresh_mode = google_signin.refresh
        access_token = create_access_token(
            user.id, 
            expires_delta=None if not refresh_mode else settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        
        logger.info(f"Google authentication successful for user ID: {user.id}")
        return True, {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "is_new_user": is_new_user
        }
    except Exception as e:
        logger.error(f"Google authentication error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        if hasattr(e, "__traceback__"):
            import traceback
            logger.error("Traceback: " + "".join(traceback.format_tb(e.__traceback__)))
        return False, {"error": str(e)} 