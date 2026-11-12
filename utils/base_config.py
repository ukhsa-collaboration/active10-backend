import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    app_version: str = "dev"
    app_code_commit_hash: str = "dev"

    nhs_login_authority_url: str
    nhs_login_client_id: str
    nhs_login_callback_url: str
    nhs_login_scopes: str
    nhs_api_url: str
    nhs_api_key: str
    nhs_vectors: str = '["P5.Cp.Cd"]'
    auth_jwt_secret: str
    nhs_pds_jwt_private_key: str
    db_host: str
    db_port: str
    db_user: str
    db_pass: str
    db_name: str
    db_pool_size: int = 35
    db_max_overflow: int = 10
    db_pool_recycle: int = 1800
    app_uri: str
    gojauntly_key_id: str
    gojauntly_private_key: str
    gojauntly_issuer_id: str
    aws_sqs_queue_url: str
    aws_sqs_activities_migrations_queue_url: str
    aws_sns_activity_topic_arn: str
    aws_sns_activities_migration_topic_arn: str
    sendgrid_webhook_public_key: str
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_use_ssl: bool = False

    # Keycloak (v3 API). Optional until v3 goes live; v3 stays disabled until all four are set.
    keycloak_realm_url: str | None = None
    keycloak_client_id: str | None = None
    keycloak_app_client_id: str | None = None
    session_ttl_minutes: int | None = None
    keycloak_audience: str | None = None
    keycloak_algorithms: str = "RS256"
    keycloak_required_claims: str = "scope,email,sid"
    keycloak_jwks_cache_minutes: int = 10
    keycloak_leeway_seconds: int = 10
    keycloak_http_timeout_seconds: float = 30.0

    otel_service_name: str = "active10-auth"
    otel_exporter_otlp_endpoint: str
    otel_exporter_otlp_insecure: bool = False

    test_nhs_login_api: str | None = None
    test_nhs_email: str | None = None
    test_nhs_password: str | None = None
    test_nhs_otp: str | None = None

    cprofile_enable: bool = False

    # Extra allowed for adding AWS_ local dummy secrets in the .env file
    model_config = SettingsConfigDict(
        env_file=(".env", "tests/tests.env"),
        env_file_encoding="utf-8",
        extra="allow",
    )

    @property
    def keycloak_enabled(self) -> bool:
        return all(
            (
                self.keycloak_realm_url,
                self.keycloak_client_id,
                self.keycloak_app_client_id,
                self.session_ttl_minutes,
            )
        )

    # The properties below are read only when keycloak_enabled is true.
    @property
    def keycloak_issuer(self) -> str:
        return self.keycloak_realm_url.rstrip("/")

    @property
    def keycloak_jwks_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/certs"

    @property
    def keycloak_userinfo_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/userinfo"

    @property
    def keycloak_revoke_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/revoke"

    @property
    def keycloak_expected_audience(self) -> str:
        return self.keycloak_audience or self.keycloak_client_id

    @property
    def keycloak_algorithm_list(self) -> list[str]:
        return [item.strip() for item in self.keycloak_algorithms.split(",") if item.strip()]

    @property
    def keycloak_required_claim_list(self) -> list[str]:
        return [item.strip() for item in self.keycloak_required_claims.split(",") if item.strip()]

    @property
    def jwks_cache_ttl_seconds(self) -> int:
        return self.keycloak_jwks_cache_minutes * 60

    @property
    def session_ttl_seconds(self) -> int:
        return self.session_ttl_minutes * 60


config = Config()


logger = logging.getLogger("Application-Logs")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
