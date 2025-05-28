from fastapi import Request
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get request details
        path = request.url.path
        query_string = request.url.query
        method = request.method
        
        # Log request details
        logger.info(f"Request: {method} {path} {query_string}")
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response status code and processing time
        logger.info(f"Response: {response.status_code} in {process_time:.4f}s")
        
        return response 