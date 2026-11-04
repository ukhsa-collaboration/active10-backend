from uuid import uuid4

import fakeredis
import pytest

from auth.v3.session_store import (
    delete_session,
    delete_user_sessions,
    get_session,
    get_user_session_ids,
    save_session,
    session_key,
    user_sessions_key,
)
from schemas.user import SessionUser
from utils.base_config import config

KEYCLOAK_SUB = "3a8d2869-0b2e-485a-9e67-8a906e6194ce"


@pytest.fixture(name="redis_client")
def redis_client_fixture():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    client.flushall()


def build_session(email: str | None = "default@example.com") -> SessionUser:
    return SessionUser(user_id=uuid4(), keycloak_sub=KEYCLOAK_SUB, user_email=email)


def test_keys_use_the_active10_prefix():
    assert session_key("sid-1") == "active10:sid-1"
    assert user_sessions_key(KEYCLOAK_SUB) == f"active10:user:{KEYCLOAK_SUB}"


def test_saved_session_is_returned_with_a_ttl(redis_client):
    session = build_session()

    save_session(redis_client, "sid-1", session)

    assert get_session(redis_client, "sid-1") == session
    assert redis_client.ttl(session_key("sid-1")) == config.session_ttl_seconds


def test_session_without_an_email_round_trips(redis_client):
    session = build_session(email=None)

    save_session(redis_client, "sid-1", session)

    assert get_session(redis_client, "sid-1") == session


def test_missing_session_returns_none(redis_client):
    assert get_session(redis_client, "sid-unknown") is None


def test_saved_session_is_indexed_against_the_subject(redis_client):
    save_session(redis_client, "sid-1", build_session())
    save_session(redis_client, "sid-2", build_session())

    assert redis_client.smembers(user_sessions_key(KEYCLOAK_SUB)) == {"sid-1", "sid-2"}
    assert redis_client.ttl(user_sessions_key(KEYCLOAK_SUB)) == config.session_ttl_seconds


def test_deleting_a_session_clears_its_index_entry(redis_client):
    save_session(redis_client, "sid-1", build_session())
    save_session(redis_client, "sid-2", build_session())

    removed = delete_session(redis_client, "sid-1")

    assert removed is not None
    assert removed.keycloak_sub == KEYCLOAK_SUB
    assert get_session(redis_client, "sid-1") is None
    assert redis_client.smembers(user_sessions_key(KEYCLOAK_SUB)) == {"sid-2"}


def test_deleting_an_unknown_session_is_harmless(redis_client):
    assert delete_session(redis_client, "sid-unknown") is None


def test_deleting_user_sessions_removes_every_device(redis_client):
    save_session(redis_client, "sid-1", build_session())
    save_session(redis_client, "sid-2", build_session())

    assert delete_user_sessions(redis_client, KEYCLOAK_SUB) == 2  # noqa: PLR2004
    assert get_session(redis_client, "sid-1") is None
    assert get_session(redis_client, "sid-2") is None
    assert redis_client.exists(user_sessions_key(KEYCLOAK_SUB)) == 0


def test_replacing_user_sessions_leaves_only_the_new_one(redis_client):
    save_session(redis_client, "sid-old", build_session())
    new_session = build_session()

    delete_user_sessions(redis_client, KEYCLOAK_SUB)
    save_session(redis_client, "sid-new", new_session)

    assert get_session(redis_client, "sid-old") is None
    assert get_session(redis_client, "sid-new") == new_session
    assert get_user_session_ids(redis_client, KEYCLOAK_SUB) == {"sid-new"}


def test_live_session_ids_are_listed(redis_client):
    save_session(redis_client, "sid-1", build_session())
    save_session(redis_client, "sid-2", build_session())

    assert get_user_session_ids(redis_client, KEYCLOAK_SUB) == {"sid-1", "sid-2"}


def test_expired_sessions_are_pruned_from_the_index(redis_client):
    save_session(redis_client, "sid-1", build_session())
    save_session(redis_client, "sid-2", build_session())
    redis_client.delete(session_key("sid-1"))

    assert get_user_session_ids(redis_client, KEYCLOAK_SUB) == {"sid-2"}
    assert redis_client.smembers(user_sessions_key(KEYCLOAK_SUB)) == {"sid-2"}


def test_subject_with_no_sessions_returns_an_empty_set(redis_client):
    assert get_user_session_ids(redis_client, KEYCLOAK_SUB) == set()


def test_malformed_session_entry_is_discarded(redis_client):
    redis_client.set(session_key("sid-1"), '{"user_id": "not-a-uuid"}')

    assert get_session(redis_client, "sid-1") is None
    assert redis_client.exists(session_key("sid-1")) == 0
