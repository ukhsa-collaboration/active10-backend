from http import HTTPStatus
from types import SimpleNamespace
from typing import Annotated, Any
from uuid import uuid4

import fakeredis
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from redis import RedisError

from auth.v3 import dependencies
from auth.v3.dependencies import (
    STEP_SESSION_READ,
    get_current_user,
    get_token_claims,
)
from auth.v3.keycloak import (
    KEYCLOAK_FLOW,
    KeycloakUnavailableError,
    TokenExpiredError,
    TokenValidationError,
)
from auth.v3.session_store import get_session, save_session
from db.redis_client import get_redis
from db.session import get_db_session
from schemas.user import SessionUser
from service.open_telemetry_service import AUTH_FLOW_KEY, AUTH_STEP_KEY
from utils.base_config import config
from utils.custom_exceptions import CustomHTTPException, custom_http_exception_handler

KEYCLOAK_SUB = "3a8d2869-0b2e-485a-9e67-8a906e6194ce"
SID = "cbe1a9f4-8f8e-4f71-9d0a-1a2b3c4d5e6f"
USER_ID = uuid4()
BEARER = {"Authorization": "Bearer token"}

_exporter = InMemorySpanExporter()
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(_exporter))


class StubSession:
    def __init__(self, user=None):
        self.user = user

    def get(self, _model, _pk):
        return self.user


class BrokenRedis:
    def get(self, _key):
        raise RedisError("connection refused")


def valid_claims() -> dict[str, Any]:
    return {"sub": KEYCLOAK_SUB, "sid": SID, "email": "default@example.com", "scope": "openid"}


def raising(error: Exception):
    def raise_error(_token, _redis):
        raise error

    return raise_error


def build_client(redis_client, db_session) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(CustomHTTPException, custom_http_exception_handler)

    @app.get("/claims")
    def claims(token_claims: Annotated[dict[str, Any], Depends(get_token_claims)]):
        return token_claims

    @app.get("/me")
    def me(user: Annotated[Any, Depends(get_current_user)]):
        return {"user_id": str(user.id)}

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: redis_client
    return TestClient(app)


@pytest.fixture(name="redis_client")
def redis_client_fixture():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    client.flushall()


@pytest.fixture(name="valid_token")
def valid_token_fixture(monkeypatch):
    monkeypatch.setattr(dependencies, "decode_access_token", lambda _t, _r: valid_claims())


@pytest.fixture(name="client")
def client_fixture(redis_client, valid_token):
    return build_client(redis_client, StubSession(SimpleNamespace(id=USER_ID)))


def save_valid_session(redis_client, keycloak_sub: str = KEYCLOAK_SUB) -> None:
    session = SessionUser(user_id=USER_ID, keycloak_sub=keycloak_sub, user_email="a@b.c")
    save_session(redis_client, SID, session)


def assert_error(response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


def test_request_without_a_header_is_not_authenticated(client):
    response = client.get("/me")

    assert_error(response, HTTPStatus.UNAUTHORIZED, "NOT_AUTHENTICATED")
    assert response.headers["www-authenticate"] == "Bearer"


def test_request_with_a_basic_header_is_not_authenticated(client):
    response = client.get("/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})

    assert_error(response, HTTPStatus.UNAUTHORIZED, "NOT_AUTHENTICATED")


def test_unconfigured_keycloak_is_unavailable(client, monkeypatch):
    monkeypatch.setattr(config, "keycloak_realm_url", None)

    response = client.get("/claims", headers=BEARER)

    assert_error(response, HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")
    assert "www-authenticate" not in response.headers


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (TokenValidationError("bad"), HTTPStatus.UNAUTHORIZED, "TOKEN_INVALID"),
        (TokenExpiredError("old"), HTTPStatus.UNAUTHORIZED, "TOKEN_EXPIRED"),
        (KeycloakUnavailableError("down"), HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE"),
    ],
)
def test_token_failures_map_to_codes(client, monkeypatch, error, status_code, code):
    monkeypatch.setattr(dependencies, "decode_access_token", raising(error))

    assert_error(client.get("/claims", headers=BEARER), status_code, code)


@pytest.mark.parametrize("path", ["/claims", "/me"])
@pytest.mark.parametrize("sid", [None, ""])
def test_token_without_a_session_id_is_rejected(client, monkeypatch, path, sid):
    claims = {**valid_claims(), "sid": sid}
    monkeypatch.setattr(dependencies, "decode_access_token", lambda _t, _r: claims)

    assert_error(client.get(path, headers=BEARER), HTTPStatus.UNAUTHORIZED, "TOKEN_INVALID")


def test_valid_token_yields_claims_without_a_session(client):
    response = client.get("/claims", headers=BEARER)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == valid_claims()


def test_valid_token_without_a_session_is_rejected(client):
    assert_error(client.get("/me", headers=BEARER), HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_session_for_another_subject_is_rejected(client, redis_client):
    save_valid_session(redis_client, keycloak_sub="someone-else")

    assert_error(client.get("/me", headers=BEARER), HTTPStatus.UNAUTHORIZED, "TOKEN_INVALID")


def test_session_for_a_deleted_user_is_dropped_and_rejected(redis_client, valid_token):
    save_valid_session(redis_client)
    client = build_client(redis_client, StubSession(user=None))

    assert_error(client.get("/me", headers=BEARER), HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")
    assert get_session(redis_client, SID) is None


def test_failing_to_drop_a_stale_session_still_rejects(redis_client, valid_token, monkeypatch):
    save_valid_session(redis_client)

    def broken_delete(_redis, _sid):
        raise RedisError("connection refused")

    monkeypatch.setattr(dependencies, "delete_session", broken_delete)
    client = build_client(redis_client, StubSession(user=None))

    assert_error(client.get("/me", headers=BEARER), HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_unreachable_session_store_is_unavailable(valid_token):
    client = build_client(BrokenRedis(), StubSession(SimpleNamespace(id=USER_ID)))

    response = client.get("/me", headers=BEARER)

    assert_error(response, HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")


def test_active_session_resolves_the_user(client, redis_client):
    save_valid_session(redis_client)

    response = client.get("/me", headers=BEARER)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"user_id": str(USER_ID)}


def test_session_read_is_traced_under_the_keycloak_flow(client, redis_client):
    save_valid_session(redis_client)
    _exporter.clear()

    client.get("/me", headers=BEARER)

    span = next(s for s in _exporter.get_finished_spans() if s.name == STEP_SESSION_READ)
    assert span.attributes[AUTH_STEP_KEY] == STEP_SESSION_READ
    assert span.attributes[AUTH_FLOW_KEY] == KEYCLOAK_FLOW


def test_bearer_is_documented_as_its_own_scheme(client):
    schemes = client.app.openapi()["components"]["securitySchemes"]

    assert schemes["KeycloakBearer"] == {"type": "http", "scheme": "bearer"}
