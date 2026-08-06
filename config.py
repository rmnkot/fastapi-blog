from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # PostgreSQL (Docker Compose) — same values used by docker-compose.yml;
    # `database_url` is derived from these in Python (see below).
    postgres_user: str = "blog_user"
    postgres_password: SecretStr = SecretStr("password")
    postgres_db: str = "blog_db"
    postgres_port: int = 5432

    @computed_field
    @property
    def database_url(self) -> str:
        """Build the async SQLAlchemy URL from the POSTGRES_* components."""
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@localhost:{self.postgres_port}/{self.postgres_db}"
        )

    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # S3 Configuration
    s3_bucket_name: str
    s3_region: str = "eu-north-1"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_endpoint_url: str | None = None

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
