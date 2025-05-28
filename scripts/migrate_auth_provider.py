#!/usr/bin/env python3

"""
Migration script to update users for Google-only authentication
This script:
1. Makes the hashed_password field nullable
2. Updates existing users' auth_provider to 'google'
"""

import os
import sys
import logging
from sqlalchemy import text

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine, SessionLocal
from app.modules.user_management.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to update users for Google-only authentication"""
    logger.info("Starting auth provider migration...")
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # 1. Alter the user table to make hashed_password nullable
        # For PostgreSQL
        query = text("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;")
        db.execute(query)
        logger.info("Modified hashed_password column to be nullable")
        
        # 2. Update existing users to use google as auth_provider
        count = db.query(User).filter(User.auth_provider != 'google').update(
            {"auth_provider": "google"}
        )
        logger.info(f"Updated {count} users to use Google authentication")
        
        # Commit the transaction
        db.commit()
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration() 