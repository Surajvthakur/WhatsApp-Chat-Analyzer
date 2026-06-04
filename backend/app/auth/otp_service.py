"""
OTP Service — generation, persistence, and verification via psycopg2.

All DB calls run through asyncio.to_thread so they stay non-blocking
inside the FastAPI event loop.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
import psycopg2
import psycopg2.extras

from app.config import settings

OTP_EXPIRY_MINUTES = 5


def _get_conn():
    """Return a fresh psycopg2 connection."""
    return psycopg2.connect(settings.database_url)


def generate_otp() -> str:
    """Generate a cryptographically random 6-digit numeric OTP."""
    secret = pyotp.random_base32()
    hotp = pyotp.HOTP(secret)
    # Use counter=0 to derive a 6-digit code from the random secret
    return hotp.at(0)


def _save_otp_sync(email: str, code: str) -> None:
    """Upsert an OTP record, replacing any existing one for the same email."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    otp_id = str(uuid.uuid4())
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO "Otp" (id, code, email, "expiresAt", "createdAt")
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE
                  SET code      = EXCLUDED.code,
                      "expiresAt" = EXCLUDED."expiresAt",
                      "createdAt" = EXCLUDED."createdAt"
                """,
                (otp_id, code, email, expires_at, datetime.now(timezone.utc)),
            )
        conn.commit()
    finally:
        conn.close()


async def save_otp(email: str, code: str) -> None:
    await asyncio.to_thread(_save_otp_sync, email, code)


def _verify_otp_sync(email: str, code: str) -> bool:
    """
    Verify the OTP. Returns True if valid and not expired.
    Deletes the record on success.
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'SELECT code, "expiresAt" FROM "Otp" WHERE email = %s',
                (email,),
            )
            row = cur.fetchone()
            if row is None:
                return False

            stored_code = row["code"]
            expires_at = row["expiresAt"]

            # Make sure we compare in UTC
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) > expires_at:
                # Expired — clean up
                cur.execute('DELETE FROM "Otp" WHERE email = %s', (email,))
                conn.commit()
                return False

            if stored_code != code:
                return False

            # Valid — delete the consumed token
            cur.execute('DELETE FROM "Otp" WHERE email = %s', (email,))
            conn.commit()
            return True
    finally:
        conn.close()


async def verify_otp(email: str, code: str) -> bool:
    return await asyncio.to_thread(_verify_otp_sync, email, code)
