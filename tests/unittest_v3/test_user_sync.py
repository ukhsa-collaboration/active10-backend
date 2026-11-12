import logging
from datetime import date
from http import HTTPStatus
from uuid import uuid4

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from redis import RedisError

from auth.jwt_handler import sign_jwt
from auth.v3 import auth_service, dependencies
from auth.v3.auth_service import STEP_SESSION_WRITE
from auth.v3.keycloak import KeycloakUnavailableError, TokenValidationError
from auth.v3.session_store import get_session, get_user_session_ids, save_session
from crud.v3.user_crud import KeycloakUserCRUD
from db.redis_client import get_redis
from main import app
from models.user import User, UserStatus, UserToken
from schemas.user import SessionUser
from service.redis_service import RedisService
from tests.unittest_v3.conftest import fake_redis

HEADERS = {"Authorization": "Bearer keycloak-token"}

_exporter = InMemorySpanExporter()
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(_exporter))


def new_nhs_number() -> str:
    return str(uuid4().int)[:10]


def profile_for(keycloak_sub: str, idp_sub: str, nhs_number: str) -> dict:
    return {
        "sub": keycloak_sub,
        "idp_sub": idp_sub,
        "nhs_number": int(nhs_number),
        "given_name": "Synced",
        "email": "synced@example.com",
        "birthdate": "1990-01-01",
        "gender": "female",
        "postcode": "LS1 1AA",
        "identity_proofing_level": "P9",
    }


@pytest.fixture(autouse=True)
def clean_redis():
    fake_redis.flushall()
    yield
    fake_redis.flushall()


@pytest.fixture(name="keycloak")
def keycloak_fixture(monkeypatch):
    """A fresh Keycloak identity per test, with the token and userinfo calls stubbed."""
    keycloak_sub = str(uuid4())
    state = {
        "claims": {"sub": keycloak_sub, "sid": str(uuid4()), "email": "s@example.com"},
        "profile": profile_for(keycloak_sub, str(uuid4()), new_nhs_number()),
    }
    monkeypatch.setattr(dependencies, "decode_access_token", lambda _t, _r: state["claims"])
    monkeypatch.setattr(auth_service, "fetch_userinfo", lambda _t: state["profile"])
    return state


@pytest.fixture(name="legacy_user")
def legacy_user_fixture(db_session, keycloak):
    """An existing NHS Login user with the same NHS number, holding a cached legacy token."""
    user = User(
        unique_id=str(uuid4()),
        nhs_number=str(keycloak["profile"]["nhs_number"]),
        first_name="Legacy",
        email="legacy@example.com",
        date_of_birth=date(1985, 5, 5),
        gender="na",
        postcode="na",
        identity_level="P9",
        status=UserStatus.LOGOUT.value,
    )
    db_session.add(user)
    db_session.flush()
    legacy_token = sign_jwt(str(user.id))
    db_session.add(UserToken(user_id=user.id, token=legacy_token))
    db_session.commit()
    fake_redis.set(RedisService.hash_token(legacy_token), "cached")
    user.legacy_token = legacy_token
    return user


@pytest.fixture(name="no_legacy_cache")
def no_legacy_cache_fixture(monkeypatch):
    """Legacy auth falls through to the database, as it does once its cache entry is gone."""
    monkeypatch.setattr(RedisService, "get_client", classmethod(lambda _cls: None))


def sync(client):
    return client.post("/v3/users/sync", headers=HEADERS)


def assert_error(response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


def test_sync_creates_a_new_user_and_opens_a_session(client, db_session, keycloak):
    response = sync(client)

    assert response.status_code == HTTPStatus.OK
    assert response.headers["Cache-Control"] == "no-cache"
    body = response.json()
    assert body["first_name"] == "Synced"
    assert body["email"] == "syn...@example.com"
    assert body["identity_level"] == "P9"

    profile = keycloak["profile"]
    user = db_session.query(User).filter(User.keycloak_sub == profile["sub"]).one()
    assert user.unique_id == profile["idp_sub"]
    assert user.nhs_number == str(profile["nhs_number"])
    assert user.date_of_birth == date(1990, 1, 1)
    assert user.status == UserStatus.LOGIN.value
    assert str(user.id) == body["id"]

    session = get_session(fake_redis, keycloak["claims"]["sid"])
    assert session.user_id == user.id
    assert session.keycloak_sub == profile["sub"]


def test_sync_links_a_legacy_user_by_nhs_number(client, db_session, keycloak, legacy_user, caplog):
    original_unique_id = legacy_user.unique_id
    idp_sub = keycloak["profile"]["idp_sub"]

    with caplog.at_level(logging.INFO):
        response = sync(client)

    assert response.status_code == HTTPStatus.OK
    assert response.json()["id"] == str(legacy_user.id)
    db_session.expire_all()
    linked = db_session.get(User, legacy_user.id)
    assert linked.keycloak_sub == keycloak["profile"]["sub"]
    assert linked.unique_id == idp_sub
    assert linked.first_name == "Synced"
    assert linked.status == UserStatus.LOGIN.value
    assert db_session.query(User).filter(User.nhs_number == linked.nhs_number).count() == 1
    expected = f"Linked user {legacy_user.id}: unique_id {original_unique_id} replaced by {idp_sub}"
    assert expected in caplog.text


def test_repeat_sync_does_not_log_the_unique_id_again(client, keycloak, legacy_user, caplog):
    sync(client)
    caplog.clear()

    with caplog.at_level(logging.INFO):
        assert sync(client).status_code == HTTPStatus.OK

    assert "unique_id" not in caplog.text


def test_unique_id_taken_by_another_account_blocks_linking(
    client, db_session, keycloak, legacy_user, caplog
):
    original_unique_id = legacy_user.unique_id
    db_session.add(
        User(
            unique_id=keycloak["profile"]["idp_sub"],
            nhs_number=new_nhs_number(),
            first_name="Someone else",
            gender="na",
            identity_level="P9",
        )
    )
    db_session.commit()

    with caplog.at_level(logging.INFO):
        response = sync(client)

    assert_error(response, HTTPStatus.CONFLICT, "ACCOUNT_CONFLICT")
    db_session.expire_all()
    unchanged = db_session.get(User, legacy_user.id)
    assert (unchanged.unique_id, unchanged.keycloak_sub) == (original_unique_id, None)
    assert "replaced by" not in caplog.text


def test_sync_removes_the_legacy_token_and_its_cache_entry(
    client, db_session, keycloak, legacy_user, no_legacy_cache
):
    legacy_headers = {"Authorization": f"Bearer {legacy_user.legacy_token}"}
    assert client.get("/v1/users/", headers=legacy_headers).status_code == HTTPStatus.OK

    assert sync(client).status_code == HTTPStatus.OK

    db_session.expire_all()
    assert db_session.query(UserToken).filter(UserToken.user_id == legacy_user.id).count() == 0
    assert fake_redis.exists(RedisService.hash_token(legacy_user.legacy_token)) == 0
    assert client.get("/v1/users/", headers=legacy_headers).status_code == HTTPStatus.FORBIDDEN


def test_sync_removes_a_legacy_token_issued_after_linking(client, db_session, keycloak):
    assert sync(client).status_code == HTTPStatus.OK
    user = db_session.query(User).filter(User.keycloak_sub == keycloak["profile"]["sub"]).one()
    late_token = sign_jwt(str(user.id))
    db_session.add(UserToken(user_id=user.id, token=late_token))
    db_session.commit()

    assert sync(client).status_code == HTTPStatus.OK

    db_session.expire_all()
    assert db_session.query(UserToken).filter(UserToken.user_id == user.id).count() == 0


def test_returning_user_is_found_by_keycloak_sub(client, db_session, keycloak):
    first = sync(client).json()
    keycloak["profile"]["given_name"] = "Renamed"

    second = sync(client).json()

    assert second["id"] == first["id"]
    assert second["first_name"] == "Renamed"
    sub = keycloak["profile"]["sub"]
    assert db_session.query(User).filter(User.keycloak_sub == sub).count() == 1


def test_user_linked_to_another_subject_is_relinked(client, db_session, keycloak, legacy_user):
    old_sub, old_sid = str(uuid4()), str(uuid4())
    legacy_user.keycloak_sub = old_sub
    db_session.commit()
    save_session(fake_redis, old_sid, SessionUser(user_id=legacy_user.id, keycloak_sub=old_sub))

    assert sync(client).status_code == HTTPStatus.OK

    db_session.expire_all()
    assert db_session.get(User, legacy_user.id).keycloak_sub == keycloak["profile"]["sub"]
    assert get_session(fake_redis, old_sid) is None


def test_duplicate_nhs_number_is_a_conflict_and_changes_nothing(
    client, db_session, keycloak, legacy_user, caplog
):
    nhs_number = legacy_user.nhs_number
    duplicate = User(
        unique_id=str(uuid4()),
        nhs_number=nhs_number,
        first_name="Duplicate",
        gender="na",
        identity_level="P9",
    )
    db_session.add(duplicate)
    db_session.commit()

    with caplog.at_level(logging.WARNING):
        response = sync(client)

    assert_error(response, HTTPStatus.CONFLICT, "ACCOUNT_CONFLICT")
    db_session.expire_all()
    assert db_session.get(User, legacy_user.id).keycloak_sub is None
    assert db_session.query(UserToken).filter(UserToken.user_id == legacy_user.id).count() == 1
    assert get_session(fake_redis, keycloak["claims"]["sid"]) is None
    assert nhs_number not in caplog.text
    assert f"*******{nhs_number[-3:]}" in caplog.text


@pytest.mark.parametrize("nhs_number", [None, ""])
def test_missing_nhs_number_is_rejected(client, keycloak, nhs_number):
    keycloak["profile"]["nhs_number"] = nhs_number

    assert_error(sync(client), HTTPStatus.UNPROCESSABLE_ENTITY, "NHS_NUMBER_MISSING")


@pytest.mark.parametrize(
    "claim", ["sub", "idp_sub", "given_name", "identity_proofing_level", "birthdate", "email"]
)
def test_missing_profile_claim_is_an_incomplete_profile(client, keycloak, claim):
    keycloak["profile"].pop(claim)

    assert_error(sync(client), HTTPStatus.BAD_GATEWAY, "UPSTREAM_PROFILE_INCOMPLETE")


def test_profile_that_is_not_an_object_is_an_incomplete_profile(client, keycloak):
    keycloak["profile"] = ["not", "a", "profile"]

    assert_error(sync(client), HTTPStatus.BAD_GATEWAY, "UPSTREAM_PROFILE_INCOMPLETE")


def test_gender_and_postcode_default_to_na(client, db_session, keycloak):
    keycloak["profile"].pop("gender")
    keycloak["profile"].pop("postcode")

    assert sync(client).status_code == HTTPStatus.OK

    user = db_session.query(User).filter(User.keycloak_sub == keycloak["profile"]["sub"]).one()
    assert (user.gender, user.postcode) == ("na", "na")


def test_sync_from_another_device_evicts_the_first_session(client, keycloak):
    first_sid = keycloak["claims"]["sid"]
    sync(client)
    keycloak["claims"] = {**keycloak["claims"], "sid": str(uuid4())}

    assert sync(client).status_code == HTTPStatus.OK

    assert get_session(fake_redis, first_sid) is None
    sub = keycloak["profile"]["sub"]
    assert get_user_session_ids(fake_redis, sub) == {keycloak["claims"]["sid"]}


def test_profile_for_another_subject_is_rejected(client, keycloak):
    keycloak["profile"]["sub"] = str(uuid4())

    assert_error(sync(client), HTTPStatus.UNAUTHORIZED, "TOKEN_INVALID")
    assert get_session(fake_redis, keycloak["claims"]["sid"]) is None


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (TokenValidationError("rejected"), HTTPStatus.UNAUTHORIZED, "TOKEN_INVALID"),
        (KeycloakUnavailableError("down"), HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE"),
    ],
)
def test_userinfo_failures_map_to_codes(client, keycloak, monkeypatch, error, status_code, code):  # noqa: PLR0913
    def fail(_token):
        raise error

    monkeypatch.setattr(auth_service, "fetch_userinfo", fail)

    assert_error(sync(client), status_code, code)


def test_invalid_token_is_rejected(client, monkeypatch):
    def reject(_token, _redis):
        raise TokenValidationError("Signature verification failed")

    monkeypatch.setattr(dependencies, "decode_access_token", reject)

    assert_error(sync(client), HTTPStatus.UNAUTHORIZED, "TOKEN_INVALID")


def test_missing_header_is_not_authenticated(client):
    response = client.post("/v3/users/sync")

    assert_error(response, HTTPStatus.UNAUTHORIZED, "NOT_AUTHENTICATED")


def test_redis_down_before_linking_changes_nothing(client, db_session, keycloak, legacy_user):
    class BrokenRedis:
        def delete(self, *_keys):
            raise RedisError("connection refused")

    app.dependency_overrides[get_redis] = lambda: BrokenRedis()
    try:
        response = sync(client)
    finally:
        app.dependency_overrides[get_redis] = lambda: fake_redis

    assert_error(response, HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")
    db_session.expire_all()
    assert db_session.get(User, legacy_user.id).keycloak_sub is None
    assert db_session.query(UserToken).filter(UserToken.user_id == legacy_user.id).count() == 1


def test_redis_down_when_saving_the_session_is_unavailable(client, keycloak, monkeypatch):
    def fail(*_args, **_kwargs):
        raise RedisError("connection refused")

    monkeypatch.setattr(auth_service, "save_session", fail)

    assert_error(sync(client), HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")


def test_concurrent_first_sync_is_resolved_on_retry(client, db_session, keycloak, monkeypatch):
    profile = keycloak["profile"]
    db_session.add(
        User(
            unique_id=profile["idp_sub"],
            keycloak_sub=profile["sub"],
            nhs_number=str(profile["nhs_number"]),
            first_name="Other sync",
            gender="na",
            identity_level="P9",
        )
    )
    db_session.commit()
    real_lookup = KeycloakUserCRUD.get_user_by_keycloak_sub
    calls = []

    def miss_once(crud, keycloak_sub):
        calls.append(keycloak_sub)
        return None if len(calls) == 1 else real_lookup(crud, keycloak_sub)

    monkeypatch.setattr(KeycloakUserCRUD, "get_user_by_keycloak_sub", miss_once)
    monkeypatch.setattr(KeycloakUserCRUD, "get_users_by_nhs_number", lambda _crud, _nhs: [])

    response = sync(client)

    assert response.status_code == HTTPStatus.OK
    assert len(calls) == 2  # noqa: PLR2004
    assert db_session.query(User).filter(User.keycloak_sub == profile["sub"]).count() == 1


def test_identity_taken_by_another_account_is_a_conflict(client, db_session, keycloak):
    db_session.add(
        User(
            unique_id=keycloak["profile"]["idp_sub"],
            nhs_number=new_nhs_number(),
            first_name="Someone else",
            gender="na",
            identity_level="P9",
        )
    )
    db_session.commit()

    assert_error(sync(client), HTTPStatus.CONFLICT, "ACCOUNT_CONFLICT")


def test_session_write_is_traced(client, keycloak):
    _exporter.clear()

    sync(client)

    assert STEP_SESSION_WRITE in {span.name for span in _exporter.get_finished_spans()}


def test_failed_cache_clear_after_commit_is_only_logged(
    client, db_session, keycloak, legacy_user, caplog
):
    class FailsOnSecondDelete:
        def __init__(self):
            self.deletes = 0

        def __getattr__(self, name):
            return getattr(fake_redis, name)

        def delete(self, *keys):
            self.deletes += 1
            if self.deletes == 2:  # noqa: PLR2004
                raise RedisError("connection refused")
            return fake_redis.delete(*keys)

    redis = FailsOnSecondDelete()
    app.dependency_overrides[get_redis] = lambda: redis
    try:
        with caplog.at_level(logging.WARNING):
            response = sync(client)
    finally:
        app.dependency_overrides[get_redis] = lambda: fake_redis

    assert response.status_code == HTTPStatus.OK
    assert "Legacy auth cache clear after commit failed" in caplog.text
    db_session.expire_all()
    assert db_session.query(UserToken).filter(UserToken.user_id == legacy_user.id).count() == 0
