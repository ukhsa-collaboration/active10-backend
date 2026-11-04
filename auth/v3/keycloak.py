import json
from typing import Any

import httpx
import jwt
from jwt import ExpiredSignatureError, PyJWK, PyJWTError
from redis import Redis, RedisError

from service.open_telemetry_service import auth_step_span
from utils.base_config import config, logger

JWKS_CACHE_KEY = "active10:jwks"

KEYCLOAK_FLOW = "keycloak"
STEP_JWKS_FETCH = "keycloak-jwks-fetch"
STEP_TOKEN_VALIDATION = "keycloak-token-validation"
STEP_USERINFO = "keycloak-userinfo"
STEP_REVOKE = "keycloak-revoke"


class TokenValidationError(Exception):
    """Raised when a Keycloak token cannot be validated."""


class TokenExpiredError(TokenValidationError):
    """Raised when a Keycloak token is otherwise valid but past its expiry."""


class KeycloakUnavailableError(Exception):
    """Raised when Keycloak cannot be reached to retrieve its signing keys."""


def _fetch_jwks() -> dict[str, Any]:
    """Fetches the JWKS document from Keycloak."""
    with auth_step_span(STEP_JWKS_FETCH, flow=KEYCLOAK_FLOW):
        try:
            response = httpx.get(
                config.keycloak_jwks_url, timeout=config.keycloak_http_timeout_seconds
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.error(f"Unable to retrieve JWKS from Keycloak: {e}")
            raise KeycloakUnavailableError("Unable to retrieve signing keys") from e


def _read_cached_jwks(redis: Redis) -> dict[str, Any] | None:
    try:
        cached = redis.get(JWKS_CACHE_KEY)
    except RedisError as e:
        logger.warning(f"JWKS cache read failed, falling back to Keycloak: {e}")
        return None

    if not cached:
        return None

    try:
        return json.loads(cached)
    except json.JSONDecodeError:
        logger.warning("Discarding malformed JWKS cache entry")
        return None


def _write_cached_jwks(redis: Redis, jwks: dict[str, Any]) -> None:
    try:
        redis.set(JWKS_CACHE_KEY, json.dumps(jwks), ex=config.jwks_cache_ttl_seconds)
    except RedisError as e:
        logger.warning(f"JWKS cache write failed: {e}")


def get_jwks(redis: Redis, refresh: bool = False) -> dict[str, Any]:
    """Returns the Keycloak JWKS, from the Redis cache unless a refresh is requested."""
    if not refresh:
        cached = _read_cached_jwks(redis)
        if cached:
            return cached

    jwks = _fetch_jwks()
    _write_cached_jwks(redis, jwks)
    return jwks


def _select_signing_key(jwks: dict[str, Any], kid: str) -> dict[str, Any] | None:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid and key.get("use", "sig") == "sig":
            return key
    return None


def get_signing_key(redis: Redis, kid: str) -> PyJWK:
    """
    Resolves the signing key for a key id, refreshing the cache once when the key id is
    unknown so that Keycloak key rotation does not reject otherwise valid tokens.
    """
    key = _select_signing_key(get_jwks(redis), kid)
    if key is None:
        key = _select_signing_key(get_jwks(redis, refresh=True), kid)

    if key is None:
        raise TokenValidationError("Signing key not found for token")

    try:
        return PyJWK.from_dict(key)
    except PyJWTError as e:
        raise TokenValidationError("Unusable signing key") from e


def decode_access_token(token: str, redis: Redis) -> dict[str, Any]:
    """Validates a Keycloak access token and returns its claims."""
    with auth_step_span(STEP_TOKEN_VALIDATION, flow=KEYCLOAK_FLOW):
        try:
            kid = jwt.get_unverified_header(token).get("kid")
        except PyJWTError as e:
            raise TokenValidationError("Malformed token header") from e

        if not kid:
            raise TokenValidationError("Token header is missing kid")

        signing_key = get_signing_key(redis, kid)

        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=config.keycloak_algorithm_list,
                audience=config.keycloak_expected_audience,
                issuer=config.keycloak_issuer,
                leeway=config.keycloak_leeway_seconds,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except ExpiredSignatureError as e:
            raise TokenExpiredError("Token has expired") from e
        except PyJWTError as e:
            raise TokenValidationError(str(e)) from e

        missing = [
            claim for claim in config.keycloak_required_claim_list if claims.get(claim) is None
        ]
        if missing:
            raise TokenValidationError(f"Token is missing required claims: {', '.join(missing)}")

        return claims


def fetch_userinfo(token: str) -> dict[str, Any]:
    """Returns the Keycloak userinfo profile for an access token."""
    with auth_step_span(STEP_USERINFO, flow=KEYCLOAK_FLOW):
        try:
            response = httpx.get(
                config.keycloak_userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=config.keycloak_http_timeout_seconds,
            )
        except httpx.HTTPError as e:
            logger.error(f"Unable to reach Keycloak userinfo endpoint: {e}")
            raise KeycloakUnavailableError("Unable to retrieve user profile") from e

        if response.status_code in (401, 403):
            raise TokenValidationError("Token rejected by Keycloak")

        try:
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as e:
            logger.error(f"Unexpected response from Keycloak userinfo endpoint: {e}")
            raise KeycloakUnavailableError("Unable to retrieve user profile") from e


def revoke_refresh_token(refresh_token: str) -> None:
    """
    Revokes a refresh token at Keycloak, as the app client that issued it. A 200 can still
    carry a rejection, so the body is read as well as the status.
    """
    with auth_step_span(STEP_REVOKE, flow=KEYCLOAK_FLOW):
        try:
            response = httpx.post(
                config.keycloak_revoke_url,
                data={
                    "client_id": config.keycloak_app_client_id,
                    "token": refresh_token,
                    "token_type_hint": "refresh_token",
                },
                timeout=config.keycloak_http_timeout_seconds,
            )
        except httpx.HTTPError as e:
            logger.error(f"Unable to reach Keycloak revoke endpoint: {e}")
            raise KeycloakUnavailableError("Unable to revoke refresh token") from e

        error = _reported_error(response)
        if error == "invalid_token":
            raise TokenValidationError("Refresh token rejected by Keycloak")
        if error:
            logger.error(
                f"Keycloak revoke endpoint reported {error} with status {response.status_code}"
            )
            raise KeycloakUnavailableError("Unable to revoke refresh token")

        try:
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Unexpected response from Keycloak revoke endpoint: {e}")
            raise KeycloakUnavailableError("Unable to revoke refresh token") from e


def _reported_error(response: httpx.Response) -> str | None:
    """Returns the OAuth error Keycloak put in the body, if any."""
    if not response.content:
        return None
    try:
        body = response.json()
    except ValueError:
        return None
    if not isinstance(body, dict) or not isinstance(body.get("error"), str):
        return None
    return body["error"]


def read_refresh_token_sid(refresh_token: str) -> str:
    """
    Returns the session id a refresh token belongs to, read without verifying it. Keycloak
    verifies the token when it is revoked, so a forged session id is caught there.
    """
    try:
        claims = jwt.decode(refresh_token, options={"verify_signature": False})
    except PyJWTError as e:
        raise TokenValidationError("Malformed refresh token") from e

    sid = claims.get("sid")
    if not isinstance(sid, str) or not sid:
        raise TokenValidationError("Refresh token has no session id")
    return sid
