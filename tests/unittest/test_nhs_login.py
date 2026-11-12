from uuid import uuid4

import pytest

from crud.token_crud import TokenCRUD
from crud.user_crud import UserCRUD
from models import User, UserToken
from service.nhs_login_service import NHSLoginService
from service.redis_service import RedisService
from tests.unittest.conftest import authenticated_user, unauthenticated_user  # noqa
from utils.base_config import config


def test_nhs_login_redirect(client):
    response = client.get("/nhs_login/test_app/12345", follow_redirects=False)

    assert response.status_code == 307  # noqa: PLR2004
    assert "https://auth.aos.signin.nhs.uk/authorize?" in response.headers["location"]


def test_nhs_login_missing_app_internal_id(client):
    response = client.get("/nhs_login/test_app", follow_redirects=False)

    assert response.status_code == 404  # noqa: PLR2004


def test_nhs_login_callback_success(client):
    response = client.get(
        "/nhs_login/callback",
        params={"code": "123", "state": "test_app_12345"},
        follow_redirects=False,
    )

    assert response.status_code == 307  # noqa: PLR2004
    assert (
        response.headers["location"]
        == "active10dev://nhs_login_callback?code=123&state=test_app_12345"
    )


def test_nhs_login_callback_missing_code(client):
    response = client.get(
        "/nhs_login/callback",
        params={"state": "test_app_12345"},
        follow_redirects=False,
    )

    assert response.status_code == 400  # noqa: PLR2004
    assert response.json() == {"detail": "Missing code"}


def test_nhs_login_callback_missing_state(client):
    response = client.get(
        "/nhs_login/callback",
        params={"code": "123"},
        follow_redirects=False,
    )

    assert response.status_code == 400  # noqa: PLR2004
    assert response.json() == {"detail": "Missing state"}


def test_nhs_login_callback_empty_query_params(client):
    response = client.get("/nhs_login/callback", follow_redirects=False, params={})

    assert response.status_code == 400  # noqa: PLR2004
    assert response.json() == {"detail": "Missing state and code"}


def test_logout_user_without_token(client):
    response = client.post("/nhs_login/logout")
    assert response.status_code == 403  # noqa: PLR2004
    assert response.json() == {"detail": "Not authenticated"}


def test_logout_with_unauthenticated_user(client, unauthenticated_user):  # noqa
    response = client.post(
        "/nhs_login/logout",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004
    assert response.json() == {"detail": "User not found"}


def test_logout_with_authenticated_user(client, authenticated_user):  # noqa
    response = client.post(
        "/nhs_login/logout",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    assert response.json() == {"message": "User logged out successfully"}


def test_disconnect_with_unauthenticated_user(client, unauthenticated_user):  # noqa
    response = client.post(
        "/nhs_login/disconnect",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004
    assert response.json() == {"detail": "User not found"}


def test_disconnect_user_without_token(client):
    response = client.post("/nhs_login/disconnect")

    assert response.status_code == 403  # noqa: PLR2004
    assert response.json() == {"detail": "Not authenticated"}


def test_disconnect_user_with_authenticated_user(client, authenticated_user):  # noqa
    response = client.post(
        "/nhs_login/disconnect",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    assert response.json() == {"message": "User disconnected successfully"}


def test_nhs_login_endpoints_have_no_cache_header(client):
    callback = client.get(
        "/nhs_login/callback",
        params={"code": "123", "state": "test_app_12345"},
        follow_redirects=False,
    )
    assert callback.headers["Cache-Control"] == "no-cache"


def test_nhs_login_error_responses_have_no_cache_header(client):
    logout = client.post("/nhs_login/logout")
    assert logout.status_code == 403  # noqa: PLR2004
    assert logout.headers["Cache-Control"] == "no-cache"

    disconnect = client.post("/nhs_login/disconnect")
    assert disconnect.status_code == 403  # noqa: PLR2004
    assert disconnect.headers["Cache-Control"] == "no-cache"


def test_no_cache_header_not_set_on_login_redirect(client):
    response = client.get("/nhs_login/test_app/12345", follow_redirects=False)

    assert "Cache-Control" not in response.headers


def test_no_cache_header_not_set_outside_nhs_login(client):
    response = client.get("/healthcheck")

    assert "Cache-Control" not in response.headers


def nhs_user_info(sub: str, nhs_number: str) -> dict:
    return {
        "sub": sub,
        "nhs_number": nhs_number,
        "given_name": "Legacy",
        "email": "legacy@example.com",
        "birthdate": "1990-01-01",
        "gender": "na",
        "postcode": "na",
        "identity_proofing_level": "P9",
    }


def new_nhs_number() -> str:
    return str(uuid4().int)[:10]


@pytest.fixture
def login_service(db_session, monkeypatch):
    service = NHSLoginService(UserCRUD(db_session), TokenCRUD(db_session, RedisService()))

    def use_user_info(user_info: dict) -> NHSLoginService:
        monkeypatch.setattr(service, "get_user_info", lambda _req_args: user_info)
        return service

    return use_user_info


def add_user(db_session, sub: str, nhs_number: str, keycloak_sub: str | None) -> User:
    user = User(
        unique_id=sub,
        nhs_number=nhs_number,
        keycloak_sub=keycloak_sub,
        first_name="Legacy",
        identity_level="P9",
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_process_callback_issues_token_for_legacy_user(db_session, login_service):
    sub, nhs_number = str(uuid4()), new_nhs_number()
    user = add_user(db_session, sub, nhs_number, keycloak_sub=None)

    redirect = login_service(nhs_user_info(sub, nhs_number)).process_callback({"code": "1"})

    assert redirect.startswith(f"{config.app_uri}nhs_user_logged_in?token=")
    assert db_session.query(UserToken).filter_by(user_id=user.id).count() == 1


def test_process_callback_refuses_user_linked_to_keycloak(db_session, login_service):
    sub, nhs_number = str(uuid4()), new_nhs_number()
    user = add_user(db_session, sub, nhs_number, keycloak_sub=str(uuid4()))

    redirect = login_service(nhs_user_info(sub, nhs_number)).process_callback({"code": "1"})

    assert redirect == f"{config.app_uri}nhs_keycloak_migrated"
    assert db_session.query(UserToken).filter_by(user_id=user.id).count() == 0


def test_process_callback_refuses_nhs_number_linked_to_keycloak(db_session, login_service):
    nhs_number = new_nhs_number()
    add_user(db_session, str(uuid4()), nhs_number, keycloak_sub=str(uuid4()))
    legacy_sub = str(uuid4())

    redirect = login_service(nhs_user_info(legacy_sub, nhs_number)).process_callback({"code": "1"})

    assert redirect == f"{config.app_uri}nhs_keycloak_migrated"
    assert db_session.query(User).filter_by(unique_id=legacy_sub).first() is None
