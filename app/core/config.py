"""
app/core/config.py

Centralized application configuration.

All environment-specific values such as database credentials,
secret keys, and API keys are loaded from the .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ---------------------------------------------------------
    # App
    # ---------------------------------------------------------
    APP_NAME: str = "SkillBridge"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ---------------------------------------------------------
    # Database
    # ---------------------------------------------------------
    DATABASE_URL: str = ""

    # ---------------------------------------------------------
    # Authentication
    # ---------------------------------------------------------
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ---------------------------------------------------------
    # AI
    # ---------------------------------------------------------
    DEEPSEEK_API_KEY: str = ""

    # ---------------------------------------------------------
    # Environment configuration
    # ---------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# -------------------------------------------------------------
# Shared settings instance
# -------------------------------------------------------------
settings = Settings()