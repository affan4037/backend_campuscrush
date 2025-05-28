import os
import subprocess
import logging
from datetime import datetime
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_database():
    """Create a backup of the current database"""
    try:
        # Extract database name from URL
        db_url = settings.DATABASE_URL
        db_name = db_url.split('/')[-1]
        
        # Create backup directory if it doesn't exist
        backup_dir = "database_backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/{db_name}_{timestamp}.sql"
        
        # Create backup using pg_dump
        cmd = [
            "pg_dump",
            "-h", db_url.split('@')[1].split(':')[0],  # host
            "-p", db_url.split(':')[3].split('/')[0],  # port
            "-U", db_url.split('://')[1].split(':')[0],  # user
            "-d", db_name,  # database
            "-f", backup_file
        ]
        
        logger.info(f"Creating database backup to {backup_file}")
        subprocess.run(cmd, check=True)
        logger.info("Backup completed successfully")
        
        return backup_file
    except Exception as e:
        logger.error(f"Error creating database backup: {e}")
        raise

if __name__ == "__main__":
    backup_database() 