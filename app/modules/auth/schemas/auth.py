from typing import Optional
from pydantic import BaseModel, EmailStr, validator

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None 

def _normalize_email(email: Optional[EmailStr]) -> Optional[str]:
    """Normalize email to lowercase."""
    return email.lower() if email else None

class GoogleSignInRequest(BaseModel):
    firebase_token: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    photo_url: Optional[str] = None
    refresh: bool = False
    
    _normalize_email = validator('email', allow_reuse=True)(_normalize_email) 