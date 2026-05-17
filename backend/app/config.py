from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cors_origins: str = "http://localhost:3000"
    session_ttl_seconds: int = 3600
    max_upload_mb: int = 50
    groq_api_key: str = ""
    groq_model: str = "llama3-8b-8192"

    model_config = {"env_file": ".env"}


settings = Settings()
