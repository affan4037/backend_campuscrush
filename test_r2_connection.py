#!/usr/bin/env python3
"""
Test script to verify Cloudflare R2 connection and configuration.
This script will check if all required environment variables are set,
attempt to connect to the R2 bucket, and perform basic operations.

Run with: python test_r2_connection.py
"""
import os
import sys
import boto3
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_r2_connection():
    """Test connection to Cloudflare R2 and verify configuration"""
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Check for required environment variables
    r2_env_vars = {
        "R2_ENDPOINT": os.getenv("R2_ENDPOINT"),
        "R2_ACCESS_KEY_ID": os.getenv("R2_ACCESS_KEY_ID"),
        "R2_SECRET_ACCESS_KEY": os.getenv("R2_SECRET_ACCESS_KEY"),
        "R2_BUCKET_NAME": os.getenv("R2_BUCKET_NAME", "campuscrush-media"),
        "R2_PUBLIC_URL": os.getenv("R2_PUBLIC_URL")
    }
    
    # Check if all required variables are set
    missing_vars = [var for var, value in r2_env_vars.items() if not value]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file or environment")
        r2_env_template = Path("r2_env_example.txt")
        if r2_env_template.exists():
            logger.info(f"You can use {r2_env_template} as a template")
        return False
    
    # Initialize R2 client
    try:
        logger.info(f"Connecting to R2 at {r2_env_vars['R2_ENDPOINT']}")
        s3 = boto3.client(
            's3',
            endpoint_url=r2_env_vars["R2_ENDPOINT"],
            aws_access_key_id=r2_env_vars["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=r2_env_vars["R2_SECRET_ACCESS_KEY"],
        )
        
        # Test bucket exists
        try:
            logger.info(f"Checking if bucket '{r2_env_vars['R2_BUCKET_NAME']}' exists")
            s3.head_bucket(Bucket=r2_env_vars["R2_BUCKET_NAME"])
            logger.info("✅ Bucket exists and is accessible")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                logger.error(f"❌ Bucket '{r2_env_vars['R2_BUCKET_NAME']}' does not exist")
                logger.info("Creating bucket...")
                try:
                    s3.create_bucket(Bucket=r2_env_vars["R2_BUCKET_NAME"])
                    logger.info(f"✅ Bucket '{r2_env_vars['R2_BUCKET_NAME']}' created successfully")
                except Exception as create_error:
                    logger.error(f"❌ Failed to create bucket: {create_error}")
                    return False
            elif error_code == "403":
                logger.error(f"❌ No permission to access bucket '{r2_env_vars['R2_BUCKET_NAME']}'")
                logger.error("Please check your access key permissions")
                return False
            else:
                logger.error(f"❌ Error accessing bucket: {e}")
                return False
        
        # Create test directories
        for prefix in ["profile_pictures", "post_media"]:
            logger.info(f"Creating test file in '{prefix}/' prefix")
            test_key = f"{prefix}/test-{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
            try:
                s3.put_object(
                    Bucket=r2_env_vars["R2_BUCKET_NAME"],
                    Key=test_key,
                    Body=f"Test file created on {datetime.now().isoformat()}",
                    ContentType="text/plain"
                )
                logger.info(f"✅ Successfully wrote test file to {test_key}")
                
                # Check public URL
                public_url = f"{r2_env_vars['R2_PUBLIC_URL']}/{test_key}"
                logger.info(f"Public URL for test file should be: {public_url}")
                logger.info("Please verify this URL is accessible in your browser")
            except Exception as e:
                logger.error(f"❌ Failed to write test file: {e}")
                return False
        
        # List objects in bucket
        try:
            logger.info(f"Listing objects in bucket '{r2_env_vars['R2_BUCKET_NAME']}'")
            response = s3.list_objects_v2(Bucket=r2_env_vars["R2_BUCKET_NAME"])
            object_count = response.get("KeyCount", 0)
            logger.info(f"✅ Found {object_count} objects in bucket")
            
            # Show some objects for debugging
            if object_count > 0:
                objects = response.get("Contents", [])
                logger.info("Sample of objects in bucket:")
                for obj in objects[:5]:  # Show up to 5 objects
                    logger.info(f"  - {obj['Key']} ({obj.get('Size', 'unknown')} bytes)")
        except Exception as e:
            logger.error(f"❌ Failed to list objects: {e}")
            return False
        
        logger.info("R2 connection test completed successfully.")
        logger.info("Your R2 storage is properly configured.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to R2: {e}")
        return False

if __name__ == "__main__":
    success = test_r2_connection()
    sys.exit(0 if success else 1) 