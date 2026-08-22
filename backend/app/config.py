from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cors_origins: str = "http://localhost:3000"
    session_ttl_seconds: int = 3600
    max_upload_mb: int = 50
    groq_api_key: str = ""
    groq_model: str = "llama3-8b-8192"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    auth_secret: str = ""
    database_url: str = ""
    
    # Embedding provider settings
    embedding_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-2"
    ollama_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "all-minilm"
    embedding_dimension: int = 384
    chunk_size: int = 15

    # Mail (SMTP) settings for OTP emails
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = ""
    mail_port: int = 465
    mail_server: str = "smtp.gmail.com"
    mail_from_name: str = "WhatsApp Chat Analyzer"
    mail_starttls: bool = False
    mail_ssl_tls: bool = True

    # JWT settings
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Rate limiting settings
    rate_limit_register_max: int = 5
    rate_limit_register_window_seconds: int = 900  # 15 minutes
    rate_limit_verify_otp_max: int = 5
    rate_limit_verify_otp_window_seconds: int = 300  # 5 minutes

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
