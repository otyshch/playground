"""
Custom middleware for the FastAPI application.
"""
import time
import logging
from typing import Dict, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Generate correlation ID for request tracking
        correlation_id = f"req_{int(time.time() * 1000000)}"
        
        # Log request
        logger.info(
            "Request started",
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=request.client.host if request.client else "unknown"
        )
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2)
        )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""
    
    def __init__(self, app, requests_per_minute: int = 100, burst_limit: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.request_counts: Dict[str, Dict[str, any]] = {}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        current_minute = int(current_time // 60)
        
        # Initialize client tracking
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {
                "minute": current_minute,
                "count": 0,
                "burst_count": 0,
                "last_request": current_time
            }
        
        client_data = self.request_counts[client_ip]
        
        # Reset count if we're in a new minute
        if client_data["minute"] != current_minute:
            client_data["minute"] = current_minute
            client_data["count"] = 0
        
        # Reset burst count if enough time has passed (1 second)
        if current_time - client_data["last_request"] > 1:
            client_data["burst_count"] = 0
        
        # Check rate limits
        if client_data["count"] >= self.requests_per_minute:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                requests_per_minute=self.requests_per_minute,
                current_count=client_data["count"]
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute allowed",
                    "retry_after": 60 - (current_time % 60)
                },
                headers={"Retry-After": str(int(60 - (current_time % 60)))}
            )
        
        if client_data["burst_count"] >= self.burst_limit:
            logger.warning(
                "Burst limit exceeded",
                client_ip=client_ip,
                burst_limit=self.burst_limit,
                current_burst=client_data["burst_count"]
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Burst limit exceeded",
                    "message": f"Maximum {self.burst_limit} requests per second allowed",
                    "retry_after": 1
                },
                headers={"Retry-After": "1"}
            )
        
        # Update counters
        client_data["count"] += 1
        client_data["burst_count"] += 1
        client_data["last_request"] = current_time
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - client_data["count"])
        )
        response.headers["X-RateLimit-Reset"] = str(int((current_minute + 1) * 60))
        
        return response
    
    def cleanup_old_entries(self):
        """Clean up old entries from rate limit tracking."""
        current_minute = int(time.time() // 60)
        clients_to_remove = []
        
        for client_ip, data in self.request_counts.items():
            # Remove entries older than 5 minutes
            if current_minute - data["minute"] > 5:
                clients_to_remove.append(client_ip)
        
        for client_ip in clients_to_remove:
            del self.request_counts[client_ip]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response