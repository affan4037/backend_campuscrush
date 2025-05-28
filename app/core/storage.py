import os
import uuid
import boto3
import logging
import traceback
from fastapi import UploadFile, HTTPException
from .config import settings

# Configure more detailed logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)

class R2Storage:
    """Handles file storage using Cloudflare R2"""
    
    def __init__(self):
        """Initialize the R2 client with settings from config"""
        self.client = None
        self.bucket = settings.R2_BUCKET_NAME
        self.public_url = settings.R2_PUBLIC_URL
        self.base_url = settings.BASE_URL
        
        # Log configuration parameters
        logger.info("Initializing R2Storage with configuration:")
        logger.info(f"  Bucket: {self.bucket}")
        logger.info(f"  Public URL: {self.public_url}")
        logger.info(f"  API Base URL: {self.base_url}")
        logger.info(f"  Endpoint: {settings.R2_ENDPOINT}")
        logger.info(f"  Access Key ID: {settings.R2_ACCESS_KEY_ID[:5]}..." if settings.R2_ACCESS_KEY_ID else "  Access Key ID: Not set")
        logger.info(f"  Secret Access Key: {'*****' if settings.R2_SECRET_ACCESS_KEY else 'Not set'}")
        
        # Check for Asia-Pacific region
        if settings.R2_ENDPOINT and '.ap.' not in settings.R2_ENDPOINT and 'ap.r2.cloudflarestorage' not in settings.R2_ENDPOINT:
            logger.warning("Endpoint URL doesn't include Asia-Pacific region (.ap.) - this might cause issues if your bucket is in the AP region")
        
        # Disabled R2 connection for local development
        logger.warning("R2 storage connection disabled for local development")
        
        """
        if all([settings.R2_ENDPOINT, settings.R2_ACCESS_KEY_ID, settings.R2_SECRET_ACCESS_KEY]):
            try:
                logger.info("Creating S3 client for R2 storage...")
                self.client = boto3.client(
                    's3',
                    endpoint_url=settings.R2_ENDPOINT,
                    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY
                )
                logger.info(f"R2Storage S3 client initialized successfully")
                
                # Test connection by listing buckets
                try:
                    response = self.client.list_buckets()
                    available_buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
                    logger.info(f"Successfully connected to R2. Available buckets: {available_buckets}")
                    
                    if self.bucket in available_buckets:
                        logger.info(f"✅ Target bucket '{self.bucket}' found and accessible")
                    else:
                        logger.warning(f"⚠️ Target bucket '{self.bucket}' not found in available buckets: {available_buckets}")
                except Exception as e:
                    logger.error(f"Failed to list buckets: {str(e)}")
                    logger.error(traceback.format_exc())
            except Exception as e:
                logger.error(f"Failed to create S3 client: {str(e)}")
                logger.error(traceback.format_exc())
                logger.warning("R2 storage will not be available due to initialization failure")
        else:
            missing = []
            if not settings.R2_ENDPOINT:
                missing.append("R2_ENDPOINT")
            if not settings.R2_ACCESS_KEY_ID:
                missing.append("R2_ACCESS_KEY_ID")
            if not settings.R2_SECRET_ACCESS_KEY:
                missing.append("R2_SECRET_ACCESS_KEY")
            logger.warning(f"R2 storage not properly configured - missing: {', '.join(missing)}")
        """
    
    async def upload_file(self, file: UploadFile, prefix="post_media") -> str:
        """Upload a file to R2 and return the public URL"""
        if not self.client:
            logger.error("Attempted to upload file but R2 client is not initialized")
            raise HTTPException(status_code=500, detail="R2 storage not configured")
            
        # Generate path with unique filename
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        key = f"{prefix}/{unique_filename}"
        
        logger.info(f"Uploading file '{file.filename}' to R2 bucket '{self.bucket}' with key '{key}'")
        
        try:
            # Upload to R2
            content = await file.read()
            logger.debug(f"Read {len(content)} bytes from file")
            
            logger.debug(f"Putting object in bucket with content type: {file.content_type}")
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=file.content_type or 'application/octet-stream'
            )
            logger.info(f"Successfully uploaded file to R2")
            
            # Reset file pointer for potential subsequent operations
            await file.seek(0)
            
            # Generate both direct R2 URL and proxy URL
            r2_public_url = f"{self.public_url}/{key}"
            proxy_url = f"{self.base_url}{settings.API_V1_STR}/media/{key}"
            
            logger.info(f"Generated public R2 URL: {r2_public_url}")
            logger.info(f"Generated proxy URL: {proxy_url}")
            
            # If R2 public URL is configured, prefer that for direct access
            if self.public_url:
                logger.info(f"Using R2 public URL for direct access") 
                return r2_public_url
            else:
                # Fall back to proxy URL if no R2 public URL is configured
                logger.info(f"R2 public URL not configured, using proxy URL")
                return proxy_url
                
        except Exception as e:
            logger.error(f"Failed to upload to R2: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Failed to upload media: {str(e)}")
    
    def delete_file(self, url: str) -> bool:
        """Delete a file from R2 using its URL"""
        if not self.client:
            logger.error("Attempted to delete file but R2 client is not initialized")
            return False
            
        if not url:
            logger.error("No URL provided for file deletion")
            return False
        
        # Get key from URL
        key = None
        
        # Handle direct R2 URL
        if self.public_url and self.public_url in url:
            key = url.replace(f"{self.public_url}/", "")
        # Handle proxy URL
        elif f"{self.base_url}{settings.API_V1_STR}/media/" in url:
            key = url.replace(f"{self.base_url}{settings.API_V1_STR}/media/", "")
        # Neither pattern matched
        else:
            logger.error(f"URL {url} doesn't match any expected URL pattern")
            return False
            
        try:
            logger.info(f"Deleting file with key '{key}' from bucket '{self.bucket}'")
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key
            )
            logger.info(f"Successfully deleted file from R2")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from R2: {str(e)}")
            logger.error(traceback.format_exc())
            return False

# Global instance for app-wide usage
r2_storage = R2Storage()
logger.info("R2Storage initialization complete") 