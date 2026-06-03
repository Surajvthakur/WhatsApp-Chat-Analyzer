import time
import json
from jose import jwe
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request

from app.config import settings

_derived_keys_cache = {}

def get_derived_encryption_key(secret: str, salt: str) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=64,  # A256CBC-HS512 needs a 64-byte key
        salt=salt.encode("utf-8"),
        info=f"Auth.js Generated Encryption Key ({salt})".encode("utf-8"),
    )
    return hkdf.derive(secret.encode("utf-8"))

def get_cached_derived_key(secret: str, salt: str) -> bytes:
    cache_key = (secret, salt)
    if cache_key not in _derived_keys_cache:
        _derived_keys_cache[cache_key] = get_derived_encryption_key(secret, salt)
    return _derived_keys_cache[cache_key]

class TokenValidationError(Exception):
    pass

class TokenExpiredError(TokenValidationError):
    pass

def verify_nextauth_token(token: str, secret: str) -> dict:
    salts = [
        "authjs.session-token",
        "__Secure-authjs.session-token",
        "next-auth.session-token",
        "__Secure-next-auth.session-token"
    ]
    
    last_error = None
    for salt in salts:
        try:
            key = get_cached_derived_key(secret, salt)
            decrypted_bytes = jwe.decrypt(token, key)
            payload = json.loads(decrypted_bytes.decode("utf-8"))
            
            # Check expiration
            if "exp" in payload and payload["exp"] < time.time():
                raise TokenExpiredError("Token has expired")
                
            return payload
        except TokenExpiredError as e:
            raise e
        except Exception as e:
            last_error = e
            continue
            
    raise TokenValidationError(f"Invalid token or decryption failed: {str(last_error)}")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Allow OPTIONS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # 2. Allow public paths
        path = request.url.path
        if path in ["/health", "/docs", "/redoc", "/openapi.json"] or path.startswith("/docs"):
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
                content={"detail": "Invalid Authorization header format. Must start with Bearer"}
            )
            
        token = auth_header[7:]
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token is missing from Authorization header"}
            )
            
        # 4. Verify token
        try:
            secret = settings.auth_secret
            if not secret:
                print("WARNING: AUTH_SECRET is not configured on the backend.")
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Auth secret is not configured on the server"}
                )
                
            user_payload = verify_nextauth_token(token, secret)
            request.state.user = user_payload
            
        except TokenExpiredError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token has expired"}
            )
        except TokenValidationError as e:
            return JSONResponse(
                status_code=401,
                content={"detail": f"Unauthorized: {str(e)}"}
            )
            
        return await call_next(request)
