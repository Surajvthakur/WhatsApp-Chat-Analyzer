import logging
import httpx
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.config import settings

logger = logging.getLogger(__name__)

clean_username = settings.mail_username.strip('"\' ')
clean_password = settings.mail_password.strip('"\' ').replace(" ", "")

mail_config = ConnectionConfig(
    MAIL_USERNAME=clean_username,
    MAIL_PASSWORD=clean_password,
    MAIL_FROM=settings.mail_from.strip('"\' ') or clean_username or "noreply@whatsapp-analyzer.com",
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_FROM_NAME=settings.mail_from_name,
    MAIL_STARTTLS=settings.mail_starttls,
    MAIL_SSL_TLS=settings.mail_ssl_tls,
    USE_CREDENTIALS=True if (clean_username and clean_password) else False,
    VALIDATE_CERTS=True,
)

fast_mail = FastMail(mail_config)


async def send_otp_email(email: str, code: str) -> None:
    """Send a styled HTML email containing the 6-digit OTP."""
    logger.info(f"=== OTP VERIFICATION CODE FOR {email}: [{code}] ===")

    # 1. First try relaying through Vercel API over HTTPS (Port 443 — NEVER blocked by Render)
    frontend_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    vercel_base = next((o for o in frontend_origins if "vercel.app" in o or "http" in o), None)

    if vercel_base:
        if not vercel_base.startswith("http"):
            vercel_base = f"https://{vercel_base}"
        
        vercel_endpoint = f"{vercel_base.rstrip('/')}/api/send-otp"
        logger.info(f"Attempting to relay OTP email via Vercel endpoint: {vercel_endpoint}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    vercel_endpoint,
                    json={
                        "email": email,
                        "code": code,
                        "secret": settings.auth_secret,
                    },
                )
                if res.status_code == 200:
                    logger.info(f"Successfully delivered OTP email to {email} via Vercel email relay!")
                    return
                else:
                    logger.warning(
                        f"Vercel email relay returned status {res.status_code}: {res.text}. Falling back to direct SMTP..."
                    )
        except Exception as e:
            logger.warning(f"Failed to relay email via Vercel ({e}). Falling back to direct SMTP...")

    # 2. Fallback to direct SMTP if credentials provided
    if not clean_username or not clean_password:
        logger.warning(
            f"SMTP credentials not configured. Skipping email delivery. Use OTP code [{code}] from logs to verify."
        )
        return

    try:
        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #111b21; border-radius: 16px; color: #e9edef;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="color: #25d366; font-size: 22px; margin: 0;">WhatsApp Chat Analyzer</h1>
                <p style="color: #8696a0; font-size: 13px; margin-top: 6px;">Email Verification</p>
            </div>
            <div style="background: #202c33; border-radius: 12px; padding: 28px; text-align: center;">
                <p style="color: #e9edef; font-size: 15px; margin: 0 0 20px;">Your verification code is:</p>
                <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #25d366; padding: 12px 0;">
                    {code}
                </div>
                <p style="color: #8696a0; font-size: 12px; margin-top: 20px;">
                    This code expires in <strong style="color: #e9edef;">5 minutes</strong>.
                </p>
            </div>
            <p style="color: #667781; font-size: 11px; text-align: center; margin-top: 20px;">
                If you didn't request this code, you can safely ignore this email.
            </p>
        </div>
        """

        message = MessageSchema(
            subject="Your Verification Code — WhatsApp Chat Analyzer",
            recipients=[email],
            body=html,
            subtype=MessageType.html,
        )

        await fast_mail.send_message(message)
        logger.info(f"Successfully delivered OTP email to {email} via direct SMTP")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email} via direct SMTP: {e}. You can use OTP code [{code}] from logs.")


