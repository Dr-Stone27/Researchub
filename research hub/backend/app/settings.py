from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List, Optional
import os
from dotenv import load_dotenv
load_dotenv()  # 
 
class Settings(BaseSettings):
    # Database
    database_url: str 

    # JWT Auth
    jwt_secret_key: str = "supersecretkey"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Email
    # email_provider: Optional[str] = None
    # email_api_key: Optional[str] = None
    
    # SendGrid configuration
    # email_api_key : str = "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"
    email_api_key : str
    email_sender : str  # Must be verified in SendGrid  = "olaiwonoladayo@gmail.com"
 

    # CORS
    cors_origins: List[AnyHttpUrl] = []

    # Consolidated configuration
    model_config = ConfigDict(
        extra='allow',
        from_attributes=True,
        env_file=".env"
    )

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
        # if os.getenv("ENV", "development") == "production" and v == "supersecretkey":
        #     raise ValueError("JWT secret key must be set in production")
        return v

    model_config = ConfigDict(
        from_attributes=True,  # Replaces orm_mode
        # ... other configs ...
    )

settings = Settings() 