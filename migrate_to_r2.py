#!/usr/bin/env python3
"""
Migration script to move media files from local storage to Cloudflare R2.
Run this script once to copy all existing files to R2.
"""
import os
import mimetypes
import boto3
from pathlib import Path
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# R2 Configuration
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "campuscrush-media")

def get_mime_type(file_path):
    """Get MIME type of a file based on extension"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'

def migrate_files():
    """Migrate files from local storage to R2"""
    # Check R2 configuration
    if not all([R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME]):
        logger.error("R2 configuration missing. Please set environment variables.")
        return
    
    # Initialize R2 client
    s3 = boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    )
    
    # Directories to migrate
    directories = [
        ("uploads/post_media", "post_media"),
        ("uploads/profile_pictures", "profile_pictures")
    ]
    
    file_count = 0
    error_count = 0
    
    # Process each directory
    for local_dir, r2_prefix in directories:
        local_path = Path(local_dir)
        
        if not local_path.exists():
            logger.warning(f"Directory not found: {local_dir}")
            continue
        
        logger.info(f"Migrating files from {local_dir} to R2 {r2_prefix}/")
        
        for file_path in local_path.glob('*'):
            if not file_path.is_file():
                continue
                
            filename = file_path.name
            key = f"{r2_prefix}/{filename}"
            
            try:
                # Get MIME type
                content_type = get_mime_type(file_path)
                
                # Upload to R2
                logger.info(f"Uploading {filename} to R2...")
                with open(file_path, "rb") as f:
                    s3.put_object(
                        Bucket=R2_BUCKET_NAME,
                        Key=key,
                        Body=f,
                        ContentType=content_type
                    )
                file_count += 1
            except Exception as e:
                logger.error(f"Error uploading {filename}: {str(e)}")
                error_count += 1
    
    logger.info(f"Migration complete. Uploaded {file_count} files with {error_count} errors.")

if __name__ == "__main__":
    migrate_files() 
