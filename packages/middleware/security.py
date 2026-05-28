"""Security middleware and CORS configuration."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from packages.config.settings import settings

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Remove Server header
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS in production."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        if settings.require_https and request.url.scheme == "http":
            return Response(
                status_code=301,
                headers={"Location": request.url.replace(scheme="https")}
            )
        return await call_next(request)

def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""
    
    # CORS - Must be added first
    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            max_age=86400,  # 24 hours
            expose_headers=["Content-Length", "X-Total-Count"],
        )
    
    # Trusted hosts - Only accept requests from known hosts
    if settings.app_env == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.example.com", "localhost"],  # Configure as needed
        )
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # HTTPS redirect
    app.add_middleware(HTTPSRedirectMiddleware)
    
    logger.info("Security middleware configured")
