"""
Email configuration and OTP email sender using fastapi-mail.
"""

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.config import settings

mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_FROM_NAME=settings.mail_from_name,
    MAIL_STARTTLS=settings.mail_starttls,
    MAIL_SSL_TLS=settings.mail_ssl_tls,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

fast_mail = FastMail(mail_config)


async def send_otp_email(email: str, code: str) -> None:
    """Send a styled HTML email containing the 6-digit OTP."""
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
