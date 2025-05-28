from fastapi import Request
import logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app")

class AuthLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check for authorization header
        auth_header = request.headers.get("Authorization")
        path = request.url.path
        
        if auth_header:
            # We have an auth header
            has_auth = True
        else:
               # No auth header
            has_auth = False
            # For requests to protected endpoints, log a warning
            if "/users/" in path and not path.endswith("/"):
                logger.warning(f"Protected endpoint {path} accessed without auth header")
        
        # Process the request
        response = await call_next(request)
        
        # Log auth-related status codes
        if response.status_code in [401, 403]:
            logger.warning(f"Auth error: {response.status_code} on {path}")
        
        return response 