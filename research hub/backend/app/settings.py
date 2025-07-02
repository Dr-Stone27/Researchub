from pydantic import BaseSettings, AnyHttpUrl, validator
from typing import List, Optional
import os

class Settings(BaseSettings):
    """
    Centralized application settings loaded from environment variables or .env file.
    All secrets and config values should be defined here for auditability and scalability.
    """
    # Database
    database_url: str

    # JWT Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Email (stub for now)
    email_provider: Optional[str] = None
    email_api_key: Optional[str] = None

    # CORS
    cors_origins: List[AnyHttpUrl] = []

    class Config:
        env_file = ".env"

    @validator("jwt_secret_key", "database_url")
    def must_not_be_default(cls, v, field):
        if os.getenv("ENV", "development") == "production":
            if not v or v in {"supersecretkey", "postgresql+psycopg2://user:password@localhost/research_hub"}:
                raise ValueError(f"{field.name} must be set to a secure value in production.")
        return v

settings = Settings() 