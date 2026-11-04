from http import HTTPStatus
from uuid import uuid4

from tests.unittest_v3.test_users import assert_error, bearer

target_id = None
invalid_target_id = uuid4()


def test_get_daily_targets_before_creating_any_is_not_found(client, authenticated_user):
    response = client.get("/v3/daily_targets", headers=bearer(authenticated_user))

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")


def test_create_daily_target(client, authenticated_user):
    payload = {"daily_target": 20, "date": 12341234}

    response = client.post("/v3/daily_targets", json=payload, headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["daily_target"] == 20  # noqa: PLR2004
    global target_id  # noqa: PLW0603
    target_id = data["id"]


def test_create_duplicate_daily_target_already_exists(client, authenticated_user):
    payload = {"daily_target": 20, "date": 12341234}

    response = client.post("/v3/daily_targets", json=payload, headers=bearer(authenticated_user))

    assert_error(response, HTTPStatus.BAD_REQUEST, "ALREADY_EXISTS")


def test_create_daily_target_with_missing_body(client, authenticated_user):
    response = client.post("/v3/daily_targets", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_create_daily_target_without_a_session(client, unauthenticated_user):
    payload = {"daily_target": 20, "date": 12341234}

    response = client.post("/v3/daily_targets", json=payload, headers=bearer(unauthenticated_user))

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_daily_targets_without_token(client):
    assert_error(client.get("/v3/daily_targets"), HTTPStatus.UNAUTHORIZED, "NOT_AUTHENTICATED")


def test_get_user_all_daily_targets(client, authenticated_user):
    response = client.get("/v3/daily_targets", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) > 0


def test_get_user_daily_targets_with_a_filter(client, authenticated_user):
    response = client.get(
        "/v3/daily_targets", params={"min_daily_target": 50}, headers=bearer(authenticated_user)
    )

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")


def test_get_user_all_daily_targets_without_a_session(client, unauthenticated_user):
    response = client.get("/v3/daily_targets", headers=bearer(unauthenticated_user))

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_get_user_single_daily_target(client, authenticated_user):
    response = client.get(f"/v3/daily_targets/{target_id}", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.OK
    assert response.json()["id"] == target_id


def test_get_user_single_invalid_daily_target(client, authenticated_user):
    response = client.get(
        f"/v3/daily_targets/{invalid_target_id}", headers=bearer(authenticated_user)
    )

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")


def test_update_daily_target(client, authenticated_user):
    payload = {"date": 123499, "daily_target": 10}

    response = client.put(
        f"/v3/daily_targets/{target_id}", json=payload, headers=bearer(authenticated_user)
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["daily_target"] == 10  # noqa: PLR2004


def test_update_daily_target_without_a_session(client, unauthenticated_user):
    payload = {"daily_target": 20, "date": 12341234}

    response = client.put(
        f"/v3/daily_targets/{target_id}", json=payload, headers=bearer(unauthenticated_user)
    )

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_delete_daily_target_without_a_session(client, unauthenticated_user):
    response = client.delete(f"/v3/daily_targets/{target_id}", headers=bearer(unauthenticated_user))

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_delete_daily_target(client, authenticated_user):
    response = client.delete(f"/v3/daily_targets/{target_id}", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.NO_CONTENT


def test_delete_invalid_daily_target(client, authenticated_user):
    response = client.delete(
        f"/v3/daily_targets/{invalid_target_id}", headers=bearer(authenticated_user)
    )

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")
