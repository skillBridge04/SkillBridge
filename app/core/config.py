"""
app/core/config.py

Centralized configuration for SkillBridge.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # App settings
    APP_NAME: str = "SkillBridge"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database settings
    DATABASE_URL: str = ""

    # Authentication settings
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # AI settings: GroqCloud
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    # Environment configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Shared configuration instance
settings = Settings()