from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Identity Anomaly Detection System"
    app_env: str = "development"
    database_url: str = "sqlite:///./app.db"
    auth_secret_key: str = "change-this-local-secret"
    auth_token_ttl_minutes: int = 480
    admin_default_username: str = "admin"
    admin_default_password: str = "admin123"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
