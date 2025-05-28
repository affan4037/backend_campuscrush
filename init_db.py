"""
Database initialization script.
This script creates all database tables in the correct order.
Run this as: python init_db.py
"""

import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("db-init")

# Add current directory to path to ensure imports work
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import inspect
from app.db.session import engine, Base
from app.core.config import settings

# Import all models to ensure they're registered with SQLAlchemy
from app.modules.user_management.models.user import User
from app.modules.posts.models.post import Post
from app.modules.posts.comments.models.comment import Comment
from app.modules.posts.reactions.models.reaction import Reaction
from app.modules.notifications.models.notification import Notification
from app.modules.friendships.models.friendship import Friendship, FriendshipRequest

def init_db():
    """Initialize the database by creating all tables."""
    logger.info(f"Initializing database at: {settings.DATABASE_URL}")
    
    # Get inspector to check if tables exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    logger.info(f"Existing tables: {existing_tables}")
    
    try:
        # Create all tables
        logger.info("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("All tables created successfully")
        
        # Verify tables were created
        inspector = inspect(engine)
        tables_after = inspector.get_table_names()
        logger.info(f"Tables after creation: {tables_after}")
        
        new_tables = set(tables_after) - set(existing_tables)
        if new_tables:
            logger.info(f"Newly created tables: {new_tables}")
        else:
            logger.info("No new tables were created")
            
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting database initialization")
    success = init_db()
    if success:
        logger.info("Database initialization completed successfully")
    else:
        logger.error("Database initialization failed")
        sys.exit(1) 