from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Define your core settings here
    # CHANGED: Use lowercase field names to match usage in src/core/security.py
    secret_key: str =  ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Add these optional fields so Pydantic doesn't crash if they exist in .env
    database_url: str | None = None
    pgadmin_default_email: str | None = None
    pgadmin_default_password: str | None = None

    # CRITICAL: This tells Pydantic to ignore any other variables (like Docker specific ones)
    # case_sensitive=False allows .env vars (ALGORITHM) to map to class fields (algorithm)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


settings = Settings()