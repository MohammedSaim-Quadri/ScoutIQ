"""
Middleware for request tracking and monitoring
"""

import time
from fastapi import Request
from firebase_admin import firestore
import logging


logger = logging.getLogger(__name__)

async def track_request_middleware(request: Request, call_next, db: firestore.Client = None):
    """
    Middleware to track all API requests for monitoring
    
    Logs:
    - Request method and path
    - Response status code
    - Request duration
    - User agent
    """
    start_time = time.time()
    
    # Log request
    logger.info(f"{request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log response
        logger.info(f"{request.method} {request.url.path} - {response.status_code} ({duration:.2f}s)")
        
        # Track metrics (async, don't block response)
        if db:
            try:
                db.collection("api_metrics").add({
                    "endpoint": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "duration_seconds": round(duration, 3),
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "user_agent": request.headers.get("user-agent", "unknown")
                })
            except Exception as e:
                logger.error(f"Failed to log metrics: {e}")
        
        return response
    
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"{request.method} {request.url.path} failed ({duration:.2f}s): {e}")
        raise
