from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List, Optional
from dotenv import load_dotenv
import os

load_dotenv()

frontend_url = os.getenv("FRONTEND_URL", "http://lcoalhost:3000")


class Settings(BaseSettings):
    # Database
    database_url: str

    # JWT Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Email
    # email_provider: Optional[str] = None
    # email_api_key: Optional[str] = None

    redis_url: Optional[str] = None  # Optional Redis URL for caching

    # SendGrid configuration

    email_api_key: str
    email_sender: str  # Must be verified in SendGrid  = "olaiwonoladayo@gmail.com"

    # Cloudinary configuration
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    # CORS
    cors_origins: List[AnyHttpUrl] = ["http://localhost:3000", frontend_url]

    # Consolidated configuration
    model_config = ConfigDict(extra="allow", from_attributes=True, env_file=".env")

    @field_validator("database_url")
    def validate_db_url(cls, v):
        """Ensure we're using an async driver in production"""
        # if os.getenv("ENV", "development") == "production":
        # if "psycopg2" in v or "localhost" in v or "password" in v:
        # if True:
        #     raise ValueError("Production database must use secure remote connection")
        return v

    @field_validator("jwt_secret_key")
    def validate_jwt_secret(cls, v):
        if os.getenv("ENV", "development") == "production" and v == "supersecretkey":
            raise ValueError("JWT secret key must be set in production")
        return v


settings = Settings()
