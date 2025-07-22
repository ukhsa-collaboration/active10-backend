import secrets
from typing import Any, Annotated

from pydantic import (
    BeforeValidator,
    computed_field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./app/)
        env_file="./.env",
        env_ignore_empty=True,
        extra="ignore",
    )

    ALLOWED_CORS_ORIGINS: Annotated[list[str] | str, BeforeValidator(parse_cors)]

    AUTH_JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    AUTH_JWT_EXPIRY_IN_SECONDS: int = 2592000

    # Configure environment variable below
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASS: str = ""
    DB_NAME: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URI(self) -> str:  # noqa
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # NHS
    NHS_LOGIN_AUTHORITY_URL: str
    NHS_LOGIN_CLIENT_ID: str
    NHS_LOGIN_SCOPES: str
    NHS_LOGIN_CALLBACK_URL: str
    NHS_API_URL: str
    NHS_API_KEY: str
    APP_URI: str
    NHS_PDS_JWT_PRIVATE_KEY: str

    # NHS TESTING
    TEST_NHS_LOGIN_API: str
    TEST_NHS_EMAIL: str
    TEST_NHS_PASSWORD: str
    TEST_NHS_OTP: str


settings = Settings()  # type: ignore
