import json
import time
from typing import Any

import fakeredis
import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from redis import RedisError

from auth.v3 import keycloak
from auth.v3.keycloak import (
    JWKS_CACHE_KEY,
    KEYCLOAK_FLOW,
    STEP_JWKS_FETCH,
    STEP_REVOKE,
    STEP_TOKEN_VALIDATION,
    STEP_USERINFO,
    KeycloakUnavailableError,
    TokenExpiredError,
    TokenValidationError,
    decode_access_token,
)
from service.open_telemetry_service import AUTH_FLOW_KEY, AUTH_STEP_KEY
from utils.base_config import config

_exporter = InMemorySpanExporter()
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(_exporter))


def generate_key(kid: str) -> tuple[Any, dict[str, Any]]:
    """Returns a private key and the matching public JWK entry."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return private_key, public_jwk


def build_token(private_key: Any, kid: str, **overrides: Any) -> str:
    claims: dict[str, Any] = {
        "sub": "3a8d2869-0b2e-485a-9e67-8a906e6194ce",
        "sid": "cbe1a9f4-8f8e-4f71-9d0a-1a2b3c4d5e6f",
        "iss": config.keycloak_issuer,
        "aud": config.keycloak_expected_audience,
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
        "scope": "openid profile email",
        "email": "default@example.com",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


class FakeResponse:
    def __init__(self, status_code: int = 200, body: Any = None):
        self.status_code = status_code
        self.body = body

    def json(self) -> Any:
        return self.body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:  # noqa: PLR2004
            raise httpx.HTTPStatusError("error", request=None, response=None)


@pytest.fixture(name="span_exporter", autouse=True)
def span_exporter_fixture():
    _exporter.clear()
    yield _exporter


@pytest.fixture(name="redis_client")
def redis_client_fixture():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    client.flushall()


@pytest.fixture(name="signing_key")
def signing_key_fixture():
    return generate_key("primary-kid")


@pytest.fixture(name="cached_jwks")
def cached_jwks_fixture(redis_client, signing_key):
    _, public_jwk = signing_key
    redis_client.set(JWKS_CACHE_KEY, json.dumps({"keys": [public_jwk]}))
    return redis_client


def test_cached_jwks_is_used_without_calling_keycloak(cached_jwks, signing_key, monkeypatch):
    monkeypatch.setattr(
        keycloak, "_fetch_jwks", lambda: pytest.fail("Keycloak should not be called")
    )
    private_key, _ = signing_key

    claims = decode_access_token(build_token(private_key, "primary-kid"), cached_jwks)

    assert claims["sid"] == "cbe1a9f4-8f8e-4f71-9d0a-1a2b3c4d5e6f"
    assert claims["email"] == "default@example.com"


def test_jwks_is_fetched_and_cached_on_a_miss(redis_client, signing_key, monkeypatch):
    private_key, public_jwk = signing_key
    jwks_response = FakeResponse(body={"keys": [public_jwk]})
    monkeypatch.setattr(keycloak.httpx, "get", lambda *_a, **_k: jwks_response)

    decode_access_token(build_token(private_key, "primary-kid"), redis_client)

    assert json.loads(redis_client.get(JWKS_CACHE_KEY)) == {"keys": [public_jwk]}
    assert redis_client.ttl(JWKS_CACHE_KEY) == config.jwks_cache_ttl_seconds


def test_fetch_calls_the_realm_jwks_url(redis_client, signing_key, monkeypatch):
    private_key, public_jwk = signing_key

    def fake_get(url, timeout):
        fake_get.called = {"url": url, "timeout": timeout}
        return FakeResponse(body={"keys": [public_jwk]})

    monkeypatch.setattr(keycloak.httpx, "get", fake_get)

    decode_access_token(build_token(private_key, "primary-kid"), redis_client)

    assert fake_get.called == {
        "url": f"{config.keycloak_issuer}/protocol/openid-connect/certs",
        "timeout": config.keycloak_http_timeout_seconds,
    }


def test_unknown_kid_refreshes_the_cache_before_failing(cached_jwks, monkeypatch):
    rotated_private_key, rotated_jwk = generate_key("rotated-kid")
    monkeypatch.setattr(keycloak, "_fetch_jwks", lambda: {"keys": [rotated_jwk]})

    claims = decode_access_token(build_token(rotated_private_key, "rotated-kid"), cached_jwks)

    assert claims["sub"] == "3a8d2869-0b2e-485a-9e67-8a906e6194ce"
    assert json.loads(cached_jwks.get(JWKS_CACHE_KEY)) == {"keys": [rotated_jwk]}


def test_unknown_kid_is_rejected_when_refresh_does_not_help(cached_jwks, monkeypatch):
    other_private_key, _ = generate_key("unpublished-kid")
    monkeypatch.setattr(keycloak, "_fetch_jwks", lambda: {"keys": []})

    with pytest.raises(TokenValidationError, match="Signing key not found"):
        decode_access_token(build_token(other_private_key, "unpublished-kid"), cached_jwks)


def test_encryption_keys_are_not_used_for_verification(redis_client, signing_key, monkeypatch):
    private_key, public_jwk = signing_key
    encryption_jwk = {**public_jwk, "use": "enc", "alg": "RSA-OAEP"}
    redis_client.set(JWKS_CACHE_KEY, json.dumps({"keys": [encryption_jwk]}))
    monkeypatch.setattr(keycloak, "_fetch_jwks", lambda: {"keys": [encryption_jwk]})

    with pytest.raises(TokenValidationError, match="Signing key not found"):
        decode_access_token(build_token(private_key, "primary-kid"), redis_client)


def test_key_without_use_can_verify(redis_client, signing_key):
    private_key, public_jwk = signing_key
    unmarked_jwk = {key: value for key, value in public_jwk.items() if key != "use"}
    redis_client.set(JWKS_CACHE_KEY, json.dumps({"keys": [unmarked_jwk]}))

    assert decode_access_token(build_token(private_key, "primary-kid"), redis_client)["sub"]


def test_unusable_published_key_is_rejected(redis_client, signing_key):
    private_key, _ = signing_key
    broken_jwk = {"kid": "primary-kid", "use": "sig", "kty": "unsupported"}
    redis_client.set(JWKS_CACHE_KEY, json.dumps({"keys": [broken_jwk]}))

    with pytest.raises(TokenValidationError, match="Unusable signing key"):
        decode_access_token(build_token(private_key, "primary-kid"), redis_client)


def test_token_signed_by_another_key_is_rejected(cached_jwks):
    forged_private_key, _ = generate_key("primary-kid")

    with pytest.raises(TokenValidationError, match="Signature verification failed"):
        decode_access_token(build_token(forged_private_key, "primary-kid"), cached_jwks)


def test_hmac_signed_token_is_rejected(cached_jwks):
    token = jwt.encode(
        {"sub": "x"}, "a-shared-secret-of-at-least-32-bytes", "HS256", {"kid": "primary-kid"}
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(token, cached_jwks)


def test_expired_token_is_rejected(cached_jwks, signing_key):
    private_key, _ = signing_key
    expired = build_token(private_key, "primary-kid", exp=int(time.time()) - 60)

    with pytest.raises(TokenExpiredError):
        decode_access_token(expired, cached_jwks)


@pytest.mark.parametrize("audience", ["account", "some-other-client"])
def test_token_for_another_audience_is_rejected(cached_jwks, signing_key, audience):
    private_key, _ = signing_key
    token = build_token(private_key, "primary-kid", aud=audience)

    with pytest.raises(TokenValidationError, match="Audience doesn't match"):
        decode_access_token(token, cached_jwks)


def test_token_from_another_issuer_is_rejected(cached_jwks, signing_key):
    private_key, _ = signing_key
    token = build_token(private_key, "primary-kid", iss="https://elsewhere.example.com/realms/x")

    with pytest.raises(TokenValidationError, match="Invalid issuer"):
        decode_access_token(token, cached_jwks)


@pytest.mark.parametrize("claim", ["exp", "iat", "iss", "aud", "sub"])
def test_token_missing_a_registered_claim_is_rejected(cached_jwks, signing_key, claim):
    private_key, _ = signing_key
    unverified = {"verify_signature": False}
    claims = jwt.decode(build_token(private_key, "primary-kid"), options=unverified)
    claims.pop(claim)
    token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "primary-kid"})

    with pytest.raises(TokenValidationError):
        decode_access_token(token, cached_jwks)


@pytest.mark.parametrize("claim", ["scope", "email", "sid"])
def test_token_missing_a_configured_claim_is_rejected(cached_jwks, signing_key, claim):
    private_key, _ = signing_key
    token = build_token(private_key, "primary-kid", **{claim: None})

    with pytest.raises(TokenValidationError, match=f"missing required claims: {claim}"):
        decode_access_token(token, cached_jwks)


def test_token_without_kid_is_rejected(cached_jwks, signing_key):
    private_key, _ = signing_key
    token = jwt.encode({"sub": "x"}, private_key, algorithm="RS256")

    with pytest.raises(TokenValidationError, match="missing kid"):
        decode_access_token(token, cached_jwks)


def test_malformed_token_is_rejected(cached_jwks):
    with pytest.raises(TokenValidationError, match="Malformed token header"):
        decode_access_token("not-a-jwt", cached_jwks)


def test_token_issued_slightly_ahead_of_our_clock_is_accepted(cached_jwks, signing_key):
    private_key, _ = signing_key
    ahead = int(time.time()) + config.keycloak_leeway_seconds - 5
    token = build_token(private_key, "primary-kid", iat=ahead, exp=ahead + 300)

    assert decode_access_token(token, cached_jwks)["iat"] == ahead


def test_malformed_cache_entry_is_replaced_from_keycloak(redis_client, signing_key, monkeypatch):
    private_key, public_jwk = signing_key
    redis_client.set(JWKS_CACHE_KEY, "{not json")
    monkeypatch.setattr(keycloak, "_fetch_jwks", lambda: {"keys": [public_jwk]})

    decode_access_token(build_token(private_key, "primary-kid"), redis_client)

    assert json.loads(redis_client.get(JWKS_CACHE_KEY)) == {"keys": [public_jwk]}


def test_unreachable_redis_falls_back_to_keycloak(signing_key, monkeypatch):
    private_key, public_jwk = signing_key
    monkeypatch.setattr(keycloak, "_fetch_jwks", lambda: {"keys": [public_jwk]})

    class BrokenRedis:
        def get(self, _key):
            raise RedisError("connection refused")

        def set(self, *_args, **_kwargs):
            raise RedisError("connection refused")

    claims = decode_access_token(build_token(private_key, "primary-kid"), BrokenRedis())

    assert claims["email"] == "default@example.com"


def test_unreachable_keycloak_is_reported_as_unavailable(redis_client, signing_key, monkeypatch):
    private_key, _ = signing_key

    def fake_get(*_args, **_kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(keycloak.httpx, "get", fake_get)

    with pytest.raises(KeycloakUnavailableError):
        decode_access_token(build_token(private_key, "primary-kid"), redis_client)


def test_keycloak_error_response_is_reported_as_unavailable(redis_client, signing_key, monkeypatch):
    private_key, _ = signing_key
    monkeypatch.setattr(keycloak.httpx, "get", lambda *_a, **_k: FakeResponse(status_code=500))

    with pytest.raises(KeycloakUnavailableError):
        decode_access_token(build_token(private_key, "primary-kid"), redis_client)


def test_validation_and_fetch_are_traced_under_the_keycloak_flow(
    redis_client, signing_key, monkeypatch, span_exporter
):
    private_key, public_jwk = signing_key
    jwks_response = FakeResponse(body={"keys": [public_jwk]})
    monkeypatch.setattr(keycloak.httpx, "get", lambda *_a, **_k: jwks_response)

    decode_access_token(build_token(private_key, "primary-kid"), redis_client)

    spans = {span.name: span for span in span_exporter.get_finished_spans()}
    for step in (STEP_JWKS_FETCH, STEP_TOKEN_VALIDATION):
        assert spans[step].attributes[AUTH_STEP_KEY] == step
        assert spans[step].attributes[AUTH_FLOW_KEY] == KEYCLOAK_FLOW


def test_rejected_token_marks_the_span_without_leaking_the_token(
    cached_jwks, signing_key, span_exporter
):
    private_key, _ = signing_key
    token = build_token(private_key, "primary-kid", exp=int(time.time()) - 60)

    with pytest.raises(TokenExpiredError):
        decode_access_token(token, cached_jwks)

    span = span_exporter.get_finished_spans()[-1]
    assert span.name == STEP_TOKEN_VALIDATION
    assert span.status.status_code == StatusCode.ERROR
    assert span.status.description == "TokenExpiredError"
    assert not span.events
    assert token not in str(span.attributes)


def test_userinfo_is_requested_with_the_access_token(monkeypatch, span_exporter):
    def fake_get(url, headers, timeout):
        fake_get.called = {"url": url, "headers": headers, "timeout": timeout}
        return FakeResponse(body={"sub": "abc"})

    monkeypatch.setattr(keycloak.httpx, "get", fake_get)

    assert keycloak.fetch_userinfo("access-token") == {"sub": "abc"}
    assert fake_get.called == {
        "url": f"{config.keycloak_issuer}/protocol/openid-connect/userinfo",
        "headers": {"Authorization": "Bearer access-token"},
        "timeout": config.keycloak_http_timeout_seconds,
    }
    span = span_exporter.get_finished_spans()[-1]
    assert span.name == STEP_USERINFO
    assert span.attributes[AUTH_FLOW_KEY] == KEYCLOAK_FLOW


@pytest.mark.parametrize("status_code", [401, 403])
def test_userinfo_rejection_is_a_validation_error(monkeypatch, status_code):
    monkeypatch.setattr(
        keycloak.httpx, "get", lambda *_a, **_k: FakeResponse(status_code=status_code)
    )

    with pytest.raises(TokenValidationError, match="rejected"):
        keycloak.fetch_userinfo("access-token")


def test_unreachable_userinfo_is_reported_as_unavailable(monkeypatch):
    def fake_get(*_args, **_kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(keycloak.httpx, "get", fake_get)

    with pytest.raises(KeycloakUnavailableError):
        keycloak.fetch_userinfo("access-token")


def test_userinfo_error_status_is_reported_as_unavailable(monkeypatch):
    monkeypatch.setattr(keycloak.httpx, "get", lambda *_a, **_k: FakeResponse(status_code=500))

    with pytest.raises(KeycloakUnavailableError):
        keycloak.fetch_userinfo("access-token")


def test_userinfo_body_that_is_not_json_is_reported_as_unavailable(monkeypatch):
    class NotJson(FakeResponse):
        def json(self):
            raise ValueError("not json")

    monkeypatch.setattr(keycloak.httpx, "get", lambda *_a, **_k: NotJson())

    with pytest.raises(KeycloakUnavailableError):
        keycloak.fetch_userinfo("access-token")


class FakeRevokeResponse:
    def __init__(self, status_code: int = 200, content: bytes = b""):
        self.status_code = status_code
        self.content = content

    def json(self) -> Any:
        return json.loads(self.content)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:  # noqa: PLR2004
            raise httpx.HTTPStatusError("error", request=None, response=None)


def fake_post_returning(response: FakeRevokeResponse):
    def fake_post(url, data, timeout):
        fake_post.sent = {"url": url, "data": data, "timeout": timeout}
        return response

    return fake_post


def test_revoke_posts_the_refresh_token_as_the_app_client(monkeypatch, span_exporter):
    post = fake_post_returning(FakeRevokeResponse())
    monkeypatch.setattr(keycloak.httpx, "post", post)

    keycloak.revoke_refresh_token("refresh-token")

    assert post.sent == {
        "url": f"{config.keycloak_issuer}/protocol/openid-connect/revoke",
        "data": {
            "client_id": config.keycloak_app_client_id,
            "token": "refresh-token",
            "token_type_hint": "refresh_token",
        },
        "timeout": config.keycloak_http_timeout_seconds,
    }
    span = span_exporter.get_finished_spans()[-1]
    assert span.name == STEP_REVOKE
    assert span.attributes[AUTH_FLOW_KEY] == KEYCLOAK_FLOW


@pytest.mark.parametrize("status_code", [200, 400])
def test_revoke_rejects_a_token_keycloak_reports_as_invalid(monkeypatch, status_code):
    response = FakeRevokeResponse(status_code=status_code, content=b'{"error": "invalid_token"}')
    monkeypatch.setattr(keycloak.httpx, "post", fake_post_returning(response))

    with pytest.raises(TokenValidationError, match="rejected"):
        keycloak.revoke_refresh_token("refresh-token")


def test_revoke_reports_a_client_misconfiguration_as_unavailable(monkeypatch):
    response = FakeRevokeResponse(status_code=401, content=b'{"error": "invalid_client"}')
    monkeypatch.setattr(keycloak.httpx, "post", fake_post_returning(response))

    with pytest.raises(KeycloakUnavailableError):
        keycloak.revoke_refresh_token("refresh-token")


def test_revoke_reports_an_unreachable_keycloak(monkeypatch):
    def fake_post(*_args, **_kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(keycloak.httpx, "post", fake_post)

    with pytest.raises(KeycloakUnavailableError):
        keycloak.revoke_refresh_token("refresh-token")


def test_revoke_reports_an_unexpected_status_as_unavailable(monkeypatch):
    monkeypatch.setattr(keycloak.httpx, "post", fake_post_returning(FakeRevokeResponse(500)))

    with pytest.raises(KeycloakUnavailableError):
        keycloak.revoke_refresh_token("refresh-token")


@pytest.mark.parametrize("content", [b"[]", b"not json"])
def test_revoke_body_that_is_not_an_error_object_is_a_success(monkeypatch, content):
    response = FakeRevokeResponse(content=content)
    monkeypatch.setattr(keycloak.httpx, "post", fake_post_returning(response))

    keycloak.revoke_refresh_token("refresh-token")


def test_refresh_token_sid_is_read_without_the_signing_key(signing_key):
    private_key, _ = signing_key
    token = jwt.encode({"sid": "sid-1"}, private_key, algorithm="RS256")

    assert keycloak.read_refresh_token_sid(token) == "sid-1"


def test_expired_refresh_token_sid_is_still_read(signing_key):
    private_key, _ = signing_key
    token = jwt.encode({"sid": "sid-1", "exp": int(time.time()) - 60}, private_key, "RS256")

    assert keycloak.read_refresh_token_sid(token) == "sid-1"


@pytest.mark.parametrize("claims", [{}, {"sid": ""}, {"sid": 42}])
def test_refresh_token_without_a_usable_sid_is_rejected(signing_key, claims):
    private_key, _ = signing_key
    token = jwt.encode(claims, private_key, algorithm="RS256")

    with pytest.raises(TokenValidationError, match="no session id"):
        keycloak.read_refresh_token_sid(token)


def test_unreadable_refresh_token_is_rejected():
    with pytest.raises(TokenValidationError, match="Malformed"):
        keycloak.read_refresh_token_sid("not-a-jwt")
