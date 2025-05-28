from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging

from app.core.config import settings

logger = logging.getLogger("app")
logger.info(f"Connecting to database with URL: {settings.DATABASE_URL}")

# Create database engine with connection pool
# Check if DATABASE_URL is properly set
if not settings.DATABASE_URL:
    logger.error("DATABASE_URL is not set or empty!")
    raise ValueError("DATABASE_URL environment variable is required")

try:
    # Create engine with proper configuration for PostgreSQL
    engine = create_engine(
        settings.DATABASE_URL, 
        pool_pre_ping=True,  # Check connection before using from pool
        pool_recycle=3600,   # Recycle connections after 1 hour
        connect_args={},     # Empty connect_args for PostgreSQL
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# Create session factory for database interactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all SQLAlchemy models
Base = declarative_base()

# Database session dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#         Provides the get_db() function which is used as a FastAPI dependency
# This function creates a new database session for each request and ensures it's properly closed after the request is completed
# It uses Python's yield statement to create a context manager pattern, ensuring proper resource cleanup