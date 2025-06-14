from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from sqlalchemy import inspect

from app.core.config import settings
from app.core.storage import r2_storage
from app.db.session import engine, Base
from app.middleware.request_logging import RequestLoggingMiddleware 
from app.middleware.auth_logging import AuthLoggingMiddleware
from app.modules.auth.api.router import router as auth_router
from app.modules.user_management.api.router import router as user_router
from app.modules.posts.api.router import router as posts_router
from app.modules.posts.comments.api.router import router as comments_router
from app.modules.posts.reactions.api.router import router as reactions_router
from app.modules.friendships.api.router import router as friendships_router
from app.modules.notifications.api.router import router as notifications_router
from app.modules.home_feed.api.router import router as home_feed_router
from app.modules.friendships.models.friendship import Friendship, FriendshipRequest
from app.modules.media.router import router as media_router
from app.db.init_db import create_all_tables

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("app")

# Initialize the FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    exception_handlers={
        RequestValidationError: request_validation_exception_handler,
        HTTPException: http_exception_handler,
    },
    debug=settings.DEBUG,
    description="Social networking app for campus community",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    trailing_slash=False,
)

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting server in {settings.ENVIRONMENT} mode")
    logger.info(f"BASE_URL: {settings.BASE_URL}")
    
    create_all_tables()

# Custom middleware for request logging
class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response

# Add middleware
app.add_middleware(LogMiddleware)
app.add_middleware(AuthLoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create required directories
for directory in ["uploads/profile_pictures", "uploads/post_media"]:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Register API routers
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])
app.include_router(user_router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(posts_router, prefix=f"{settings.API_V1_STR}/posts", tags=["posts"])
app.include_router(comments_router, prefix=f"{settings.API_V1_STR}/posts/{{post_id}}/comments", tags=["comments"])
app.include_router(reactions_router, prefix=f"{settings.API_V1_STR}/posts/{{post_id}}/reactions", tags=["reactions"])
app.include_router(friendships_router, prefix=f"{settings.API_V1_STR}/friends", tags=["friendships"])
app.include_router(notifications_router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])
app.include_router(home_feed_router, prefix=f"{settings.API_V1_STR}/feed", tags=["home feed"])
app.include_router(media_router)


# @app.get("/health")
# def health_check():

#     return {"status": "ok"}

# @app.get("/api/health")
# def api_health_check():
#     return {"status": "ok"}

@app.get("/")
async def root():
    return {
        "message": "Welcome to Campus Crush",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "documentation": "/docs" if settings.DEBUG else None,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 
                                             