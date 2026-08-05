from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    database_url: str

    # PostgreSQL (Docker Compose) — same values used by docker-compose.yml;
    # DATABASE_URL above is built from these via ${VAR} expansion in .env.
    postgres_user: str = "blog_user"
    postgres_password: SecretStr = SecretStr("password")
    postgres_db: str = "blog_db"
    postgres_port: int = 5432

    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    max_upload_size_bytes: int = 5 * 1024 * 1024  # 5MB
    post_per_page: int = 5

    reset_token_expire_minutes: int = 60

    mail_server: str = "localhost"
    mail_port: int = 587
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "noreply@example.com"
    mail_use_tls: bool = True

    frontend_url: str = "http://localhost:8000"


# Loaded from .env
settings = Settings()  # type: ignore[call-arg]
