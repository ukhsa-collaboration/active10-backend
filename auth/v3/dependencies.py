from typing import Annotated, Any

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import Redis, RedisError
from sqlalchemy.orm import Session

from auth.v3.keycloak import (
    KEYCLOAK_FLOW,
    KeycloakUnavailableError,
    TokenExpiredError,
    TokenValidationError,
    decode_access_token,
)
from auth.v3.session_store import delete_session, get_session
from db.redis_client import get_redis
from db.session import get_db_session
from models.user import User
from service.open_telemetry_service import auth_step_span
from utils.base_config import config, logger
from utils.custom_exceptions import CustomHTTPException, ErrorCode

STEP_SESSION_READ = "keycloak-session-read"

SESSION_NOT_FOUND = "Session not found"
SERVICE_UNAVAILABLE = "Service temporarily unavailable"
INVALID_CREDENTIALS = "Invalid credentials"

keycloak_bearer = HTTPBearer(auto_error=False, scheme_name="KeycloakBearer")
TokenDep = Annotated[HTTPAuthorizationCredentials | None, Depends(keycloak_bearer)]


def get_auth_token(credentials: TokenDep) -> str:
    """Returns the bearer token, rejecting a missing or non-bearer Authorization header."""
    if credentials is None:
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.NOT_AUTHENTICATED,
            error_message="Not authenticated",
        )
    return credentials.credentials


def get_token_claims(
    token: Annotated[str, Depends(get_auth_token)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, Any]:
    """Validates a Keycloak access token and returns its claims."""
    if not config.keycloak_enabled:
        logger.error("Keycloak is not configured, so the v3 API is unavailable")
        raise CustomHTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            error_message=SERVICE_UNAVAILABLE,
        )

    try:
        claims = decode_access_token(token, redis)
    except KeycloakUnavailableError as e:
        logger.error(f"Keycloak signing keys unavailable: {e}")
        raise CustomHTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            error_message=SERVICE_UNAVAILABLE,
        ) from e
    except TokenExpiredError as e:
        logger.warning(f"Token validation error: {e}")
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.TOKEN_EXPIRED,
            error_message="Token expired",
        ) from e
    except TokenValidationError as e:
        logger.warning(f"Token validation error: {e}")
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.TOKEN_INVALID,
            error_message=INVALID_CREDENTIALS,
        ) from e

    # Sessions are keyed on sid, so it is required whatever KEYCLOAK_REQUIRED_CLAIMS says.
    if not claims.get("sid"):
        logger.warning("Token has no session id")
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.TOKEN_INVALID,
            error_message=INVALID_CREDENTIALS,
        )

    return claims


def get_current_user(
    session: Annotated[Session, Depends(get_db_session)],
    claims: Annotated[dict[str, Any], Depends(get_token_claims)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> User:
    """Resolves the user behind an active Keycloak session."""
    try:
        with auth_step_span(STEP_SESSION_READ, flow=KEYCLOAK_FLOW):
            active_session = get_session(redis, claims["sid"])
    except RedisError as e:
        logger.error(f"Session lookup failed: {e}")
        raise CustomHTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            error_message=SERVICE_UNAVAILABLE,
        ) from e

    if not active_session:
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.SESSION_NOT_FOUND,
            error_message=SESSION_NOT_FOUND,
        )

    if active_session.keycloak_sub != claims["sub"]:
        logger.warning(f"Session {claims['sid']} does not belong to the token subject")
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.TOKEN_INVALID,
            error_message=INVALID_CREDENTIALS,
        )

    user: User | None = session.get(User, active_session.user_id)
    if not user:
        logger.warning(f"Dropping session for deleted user {active_session.user_id}")
        try:
            delete_session(redis, claims["sid"])
        except RedisError as e:
            logger.error(f"Unable to drop session for deleted user: {e}")
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.SESSION_NOT_FOUND,
            error_message=SESSION_NOT_FOUND,
        )

    return user
