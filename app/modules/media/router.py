from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from ..core.storage import r2_storage
from ..core.config import settings
from .service import MediaService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix=f"{settings.API_V1_STR}/media", tags=["media"])

def get_media_service():
    return MediaService(r2_storage)

@router.get("/{path:path}")
async def serve_media(path: str, media_service: MediaService = Depends(get_media_service)):
    try:
        response = await media_service.get_media(path)
        
        # The service now returns either an R2 response object or a StreamingResponse.
        # We can directly return this response object.
        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"An unexpected error occurred while serving media file {path}: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while serving media file.") 