"""
Authentication router — register and verify-otp endpoints.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from jose import jwt
from pydantic import BaseModel, EmailStr
import psycopg2
import psycopg2.extras

from app.config import settings
from app.auth.otp_service import generate_otp, save_otp, verify_otp
from app.auth.email_config import send_otp_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Request / Response schemas ───────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_conn():
    return psycopg2.connect(settings.database_url)


def _create_user_if_not_exists(email: str) -> dict:
    """
    Create an inactive user if one doesn't already exist for this email.
    Returns the user row as a dict.
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT id, email, "isActive" FROM "User" WHERE email = %s', (email,))
            user = cur.fetchone()
            if user:
                return dict(user)

            # Create new inactive user
            import uuid
            user_id = str(uuid.uuid4()).replace("-", "")[:25]
            now = datetime.now(timezone.utc)
            cur.execute(
                """
                INSERT INTO "User" (id, email, "isActive", "createdAt", "updatedAt")
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, email, "isActive"
                """,
                (user_id, email, False, now, now),
            )
            user = cur.fetchone()
            conn.commit()
            return dict(user)
    finally:
        conn.close()


def _activate_user(email: str) -> dict:
    """Set isActive = True for the given email. Returns the updated user."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE "User"
                SET "isActive" = TRUE, "updatedAt" = %s
                WHERE email = %s
                RETURNING id, email, "isActive"
                """,
                (datetime.now(timezone.utc), email),
            )
            user = cur.fetchone()
            conn.commit()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return dict(user)
    finally:
        conn.close()


def _create_jwt(user_id: str, email: str) -> str:
    """Create a signed HS256 JWT."""
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.auth_secret, algorithm=settings.jwt_algorithm)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register")
async def register(body: RegisterRequest, bg: BackgroundTasks):
    """
    Register a new user (or re-send OTP for existing inactive user).
    Creates the user profile, generates a 6-digit OTP, and dispatches
    the verification email as a background task.
    """
    user = await asyncio.to_thread(_create_user_if_not_exists, body.email)



    code = generate_otp()
    await save_otp(body.email, code)

    bg.add_task(send_otp_email, body.email, code)

    return {"message": "Verification code sent", "email": body.email}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_endpoint(body: VerifyOtpRequest):
    """
    Verify the 6-digit OTP. On success, activates the user and returns
    a signed JWT access token.
    """
    is_valid = await verify_otp(body.email, body.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user = await asyncio.to_thread(_activate_user, body.email)
    token = _create_jwt(user["id"], user["email"])

    return TokenResponse(access_token=token)
