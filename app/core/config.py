"""
app/core/config.py

Centralized configuration.

Why this file exists (and why it matters for a university project):
Instead of scattering `os.getenv("SOME_KEY")` calls across the codebase,
every setting is declared ONCE here as a typed field. pydantic-settings then:
  1. Reads values from the `.env` file automatically.
  2. Validates their types (e.g. ACCESS_TOKEN_EXPIRE_MINUTES must be an int).
  3. Gives you autocomplete + type-checking everywhere you use `settings.X`.

Every later part (database, auth, AI) will import `settings` from here
instead of reading environment variables directly.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "SkillBridge"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # --- Database (Part 2 will actually use this) ---
    DATABASE_URL: str = "postgresql+psycopg://postgres.stmfskypgzrmpknbpjjc:12345678%40Skillbridge@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"

    # --- Auth (Part 3 will actually use this) ---
    SECRET_KEY: str = "43d5dcc98f45650682ea68b78fcbdbe0bb197985ff55335898612077e95b014b"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- AI (Part 6 will actually use this) ---
    DEEPSEEK_API_KEY: str = ""

    # AI/ Tells pydantic-settings to load values from a local .env file (if present)
    DEEPSEEK_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )



# A single shared instance — import this everywhere, don't instantiate Settings() again.
settings = Settings()
