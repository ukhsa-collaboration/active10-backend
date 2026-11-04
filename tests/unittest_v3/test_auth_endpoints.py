import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from uuid import uuid4

import jwt
import pytest
from redis import RedisError
from sqlalchemy.exc import SQLAlchemyError

from auth.v3 import auth_service, dependencies
from auth.v3.keycloak import KeycloakUnavailableError, TokenValidationError
from auth.v3.session_store import get_session, save_session
from models.user import DeleteAudit, User, UserDeleteReason, UserStatus
from models.walking_plan import UserWalkingPlan
from schemas.user import SessionUser
from tests.unittest_v3.conftest import fake_redis

HEADERS = {"Authorization": "Bearer keycloak-token"}
ENDPOINTS = ["/v3/auth/logout", "/v3/auth/disconnect"]
REFRESH_SIGNING_KEY = secrets.token_urlsafe(48)
REVOKE_FAILURES = [
    (TokenValidationError("rejected"), HTTPStatus.BAD_REQUEST, "REFRESH_TOKEN_INVALID"),
    (KeycloakUnavailableError("down"), HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE"),
]


def refresh_token_for(sid: str | None) -> str:
    """A Keycloak shaped refresh token. The backend never checks its signature."""
    claims = {"sub": "any-subject", "typ": "Refresh"}
    if sid is not None:
        claims["sid"] = sid
    return jwt.encode(claims, REFRESH_SIGNING_KEY, algorithm="HS512")


@dataclass
class SignedIn:
    user: User
    keycloak_sub: str
    sid: str

    @property
    def body(self) -> dict:
        return {"refresh_token": refresh_token_for(self.sid)}


@pytest.fixture(autouse=True)
def clean_redis():
    fake_redis.flushall()
    yield
    fake_redis.flushall()


@pytest.fixture(name="signed_in")
def signed_in_fixture(db_session, monkeypatch) -> SignedIn:
    """A Keycloak user with a live session, and token claims that point at it."""
    keycloak_sub, sid = str(uuid4()), str(uuid4())
    user = User(
        unique_id=str(uuid4()),
        keycloak_sub=keycloak_sub,
        nhs_number=str(uuid4().int)[:10],
        first_name="Signed",
        email="signed@example.com",
        gender="na",
        identity_level="P9",
        status=UserStatus.LOGIN.value,
    )
    db_session.add(user)
    db_session.commit()
    save_session(
        fake_redis, sid, SessionUser(user_id=user.id, keycloak_sub=keycloak_sub, user_email=None)
    )
    claims = {"sub": keycloak_sub, "sid": sid, "email": "signed@example.com", "scope": "openid"}
    monkeypatch.setattr(dependencies, "decode_access_token", lambda _t, _r: claims)
    return SignedIn(user=user, keycloak_sub=keycloak_sub, sid=sid)


@pytest.fixture(name="revoked")
def revoked_fixture(monkeypatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(auth_service, "revoke_refresh_token", calls.append)
    return calls


def failing(monkeypatch, name: str, error: Exception) -> None:
    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(auth_service, name, fail)


def assert_error(response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


def test_logout_revokes_and_closes_the_session(client, db_session, signed_in, revoked):
    body = signed_in.body

    response = client.post("/v3/auth/logout", headers=HEADERS, json=body)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"message": "User logged out successfully"}
    assert response.headers["Cache-Control"] == "no-cache"
    assert revoked == [body["refresh_token"]]
    assert get_session(fake_redis, signed_in.sid) is None
    db_session.expire_all()
    user = db_session.get(User, signed_in.user.id)
    assert user.status == UserStatus.LOGOUT.value
    assert datetime.now(timezone.utc).replace(tzinfo=None) - user.status_updated_at < timedelta(  # noqa: UP017
        minutes=1
    )


def test_logout_keeps_status_while_another_session_is_live(client, db_session, signed_in, revoked):
    other = SessionUser(user_id=signed_in.user.id, keycloak_sub=signed_in.keycloak_sub)
    save_session(fake_redis, str(uuid4()), other)

    assert client.post("/v3/auth/logout", headers=HEADERS, json=signed_in.body).status_code == 200  # noqa: PLR2004

    db_session.expire_all()
    assert db_session.get(User, signed_in.user.id).status == UserStatus.LOGIN.value


@pytest.mark.parametrize("body", [{}, {"refresh_token": ""}])
def test_logout_without_a_refresh_token_is_a_validation_error(client, signed_in, revoked, body):
    response = client.post("/v3/auth/logout", headers=HEADERS, json=body)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert revoked == []


@pytest.mark.parametrize(("error", "status_code", "code"), REVOKE_FAILURES)
def test_failed_revoke_leaves_the_session(client, signed_in, monkeypatch, error, status_code, code):  # noqa: PLR0913
    failing(monkeypatch, "revoke_refresh_token", error)

    response = client.post("/v3/auth/logout", headers=HEADERS, json=signed_in.body)

    assert_error(response, status_code, code)
    assert get_session(fake_redis, signed_in.sid) is not None


def test_logout_with_redis_down_after_revoke_is_unavailable(
    client, signed_in, revoked, monkeypatch
):
    failing(monkeypatch, "delete_session", RedisError("connection refused"))

    response = client.post("/v3/auth/logout", headers=HEADERS, json=signed_in.body)

    assert_error(response, HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")


def test_logout_without_a_session_is_rejected(client, signed_in, revoked):
    fake_redis.flushall()

    response = client.post("/v3/auth/logout", headers=HEADERS, json=signed_in.body)

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")
    assert revoked == []


def add_walking_plan(db_session, user: User) -> None:
    db_session.add(UserWalkingPlan(user_id=user.id, walking_plan_data={"weeks": 4}))
    db_session.commit()


def test_disconnect_deletes_the_user_their_data_and_sessions(
    client, db_session, signed_in, revoked
):
    user_id = signed_in.user.id
    add_walking_plan(db_session, signed_in.user)
    other = SessionUser(user_id=user_id, keycloak_sub=signed_in.keycloak_sub)
    other_sid = str(uuid4())
    save_session(fake_redis, other_sid, other)

    response = client.post("/v3/auth/disconnect", headers=HEADERS, json=signed_in.body)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"message": "User disconnected successfully"}
    assert response.headers["Cache-Control"] == "no-cache"
    assert len(revoked) == 1
    db_session.expire_all()
    assert db_session.get(User, user_id) is None
    assert db_session.query(UserWalkingPlan).filter(UserWalkingPlan.user_id == user_id).count() == 0
    audit = db_session.query(DeleteAudit).filter(DeleteAudit.user_id == user_id).one()
    assert audit.delete_reason == UserDeleteReason.DISCONNECTED.value
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # noqa: UP017
    assert now - audit.deleted_at < timedelta(minutes=1)
    assert get_session(fake_redis, signed_in.sid) is None
    assert get_session(fake_redis, other_sid) is None


@pytest.mark.parametrize(("error", "status_code", "code"), REVOKE_FAILURES)
def test_failed_revoke_leaves_the_account(  # noqa: PLR0913
    client, db_session, signed_in, monkeypatch, error, status_code, code
):
    add_walking_plan(db_session, signed_in.user)
    failing(monkeypatch, "revoke_refresh_token", error)

    response = client.post("/v3/auth/disconnect", headers=HEADERS, json=signed_in.body)

    assert_error(response, status_code, code)
    db_session.expire_all()
    assert db_session.get(User, signed_in.user.id) is not None
    walking_plans = db_session.query(UserWalkingPlan).filter(
        UserWalkingPlan.user_id == signed_in.user.id
    )
    assert walking_plans.count() == 1
    assert get_session(fake_redis, signed_in.sid) is not None


def test_database_error_on_delete_keeps_the_account_and_sessions(
    client, db_session, signed_in, revoked, monkeypatch
):
    def fail(_instance):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(db_session, "delete", fail)

    response = client.post("/v3/auth/disconnect", headers=HEADERS, json=signed_in.body)

    assert_error(response, HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR")
    monkeypatch.undo()
    db_session.expire_all()
    assert db_session.get(User, signed_in.user.id) is not None
    assert get_session(fake_redis, signed_in.sid) is not None


def test_redis_error_after_delete_still_succeeds(
    client, db_session, signed_in, revoked, monkeypatch
):
    failing(monkeypatch, "delete_user_sessions", RedisError("connection refused"))

    response = client.post("/v3/auth/disconnect", headers=HEADERS, json=signed_in.body)

    assert response.status_code == HTTPStatus.OK
    db_session.expire_all()
    assert db_session.get(User, signed_in.user.id) is None


@pytest.mark.parametrize("path", ENDPOINTS)
@pytest.mark.parametrize(
    "refresh_token",
    [refresh_token_for(str(uuid4())), refresh_token_for(None), "not-a-jwt"],
    ids=["another-session", "no-sid", "unreadable"],
)
def test_refresh_token_from_another_sign_in_is_rejected_before_keycloak(
    client, signed_in, revoked, path, refresh_token
):
    response = client.post(path, headers=HEADERS, json={"refresh_token": refresh_token})

    assert_error(response, HTTPStatus.BAD_REQUEST, "REFRESH_TOKEN_INVALID")
    assert revoked == []
    assert get_session(fake_redis, signed_in.sid) is not None


@pytest.mark.parametrize("path", ENDPOINTS)
def test_missing_header_is_not_authenticated(client, path):
    response = client.post(path, json={"refresh_token": "anything"})

    assert_error(response, HTTPStatus.UNAUTHORIZED, "NOT_AUTHENTICATED")
