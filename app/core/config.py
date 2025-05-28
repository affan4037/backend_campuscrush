# Defines application-wide settings using Pydantic's BaseSettings
# Manages environment variables for various aspects of the application:
# API configuration (version, project name)
# Security settings (secret keys, JWT algorithm)
# Database connection details
# Email service configuration
# Application-specific settings (like allowed email domains)


import os
import json
from typing import List, Union, Any, Dict

from pydantic import BaseSettings, validator
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CampusCrush API"
    VERSION: str = "0.1.0"

    # Server URLs
    BASE_URL: str = os.getenv("BASE_URL", "https://campuscrush-sb89.onrender.com")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development_secret_key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"
    
    # Firebase
    FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-service-account.json")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:root@localhost:5432/campuscrush_db")
    
    
    # CORS - Updated to include mobile app origins and Railway deployment URL
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://192.168.0.101:3000",  # Frontend on same network
        "http://localhost:3000",     # Local development
        "http://10.0.2.2:3000",      # Android emulator
        "capacitor://localhost",     # Capacitor mobile app
        "file://",                   # Mobile app local file access
        "http://localhost",          # Mobile browser testing
        "*",                         # Allow all origins in production (controlled by Railway)
    ]
    
    # Email domain restrictions
    ALLOWED_EMAIL_DOMAINS: List[str] = os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",") if os.getenv("ALLOWED_EMAIL_DOMAINS") else []
    
    # File uploads
    UPLOAD_DIRECTORY: str = os.getenv("UPLOAD_DIRECTORY", "uploads")
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5 MB
    
    # Cloudflare R2 Storage
    R2_ENDPOINT: str = os.getenv("R2_ENDPOINT", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "campuscrush-media")
    R2_PUBLIC_URL: str = os.getenv("R2_PUBLIC_URL", "")
    
    # Frontend URL for email verification links (use campuscrush:// for mobile app)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "campuscrush://")
    
    # Development settings - set these differently in production
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ["true", "1", "t"]
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        check_fields = False

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            # Handle JSON string format
            try:
                return json.loads(v)
            except:
                return []
        return v

    @validator("ALLOWED_EMAIL_DOMAINS", pre=True)
    def assemble_email_domains(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            try:
                return json.loads(v)
            except:
                # If it's a single domain, return as a list with one item
                return [v]
        return v

# Create settings instance
settings = Settings()

# Print for debugging
if settings.DEBUG:
    print(f"Environment: {settings.ENVIRONMENT}") 