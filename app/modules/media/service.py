from ..core.storage import R2Storage
from fastapi import UploadFile, HTTPException
import logging
from pathlib import Path
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

class MediaService:
    def __init__(self, r2_storage: R2Storage):
        self.r2_storage = r2_storage

    async def get_media(self, path: str):
        """Get media from R2 storage with local storage fallback"""
        # Try fetching from R2 first
        if self.r2_storage.client:
            try:
                logger.info(f"Attempting to retrieve file {path} from R2")
                response = self.r2_storage.client.get_object(
                    Bucket=self.r2_storage.bucket,
                    Key=path
                )
                logger.info(f"Successfully retrieved file {path} from R2")
                return response # Return the R2 response object
            except Exception as e:
                # Log the R2 error and fall back to local storage
                logger.warning(f"Failed to retrieve file {path} from R2: {str(e)}. Falling back to local storage.")
        else:
            logger.warning("R2 client not configured. Falling back to local storage for file {path}.")

        # Fallback to local storage
        try:
            logger.info(f"Attempting to retrieve file {path} from local storage")
            file_path = Path("uploads") / path
            if not file_path.exists():
                logger.error(f"File {path} not found in local storage")
                raise HTTPException(status_code=404, detail="File not found")
            
            # Determine content type for local file
            content_type = "application/octet-stream"
            if path.lower().endswith(('.jpg', '.jpeg')):
                content_type = "image/jpeg"
            elif path.lower().endswith('.png'):
                content_type = "image/png"
            elif path.lower().endswith('.gif'):
                content_type = "image/gif"
            # Add other types as needed

            # Read local file content
            with open(file_path, "rb") as f:
                content = f.read()

            logger.info(f"Successfully retrieved file {path} from local storage")
            # Return a StreamingResponse for local files
            return StreamingResponse(
                iter([content]),
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400", # Example cache control for local files
                    # Add other headers if necessary, like CORS
                     "Access-Control-Allow-Origin": "*",
                     "Access-Control-Allow-Methods": "GET, OPTIONS",
                     "Access-Control-Allow-Headers": "Origin, Content-Type, Accept",
                     "Content-Disposition": f"inline; filename={path.split('/')[-1]}"
                }
            )

        except Exception as e:
            logger.error(f"Failed to retrieve file {path} from local storage: {str(e)}")
            # If both R2 and local storage fail
            raise HTTPException(status_code=500, detail=f"Failed to retrieve media file: {str(e)}")

    async def upload_media(self, file: UploadFile, prefix: str = "post_media"):
        """Upload media to R2 storage"""
        if not self.r2_storage.client:
             raise HTTPException(status_code=500, detail="R2 storage not configured. Cannot upload.")
        return await self.r2_storage.upload_file(file, prefix)

    async def delete_media(self, path: str):
        """Delete media from R2 storage"""
        if not self.r2_storage.client:
            logger.warning("R2 storage not configured. Cannot delete file from R2.")
            # Optionally add local file deletion logic here if needed
            return False # Or handle local deletion
        return self.r2_storage.delete_file(path) 