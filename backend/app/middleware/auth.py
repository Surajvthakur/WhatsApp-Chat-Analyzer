import time
import json
from jose import jwt, JWTError

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request

from app.config import settings

# Paths that do not require authentication
PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/register",
    "/api/v1/auth/verify-otp",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Allow OPTIONS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # 2. Allow public paths
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/docs"):
            return await call_next(request)
            
        # 3. Read Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing Authorization header"}
            )
            
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid Authorization header format"}
            )
            
        token = auth_header[7:]
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token is missing from Authorization header"}
            )
            
        # 4. Verify HS256 JWT
        try:
            secret = settings.auth_secret
            if not secret:
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Auth secret is not configured on the server"}
                )

            payload = jwt.decode(
                token,
                secret,
                algorithms=[settings.jwt_algorithm],
            )
            request.state.user = payload
            
        except JWTError as e:
            return JSONResponse(
                status_code=401,
                content={"detail": f"Invalid or expired token: {str(e)}"}
            )
            
        return await call_next(request)
