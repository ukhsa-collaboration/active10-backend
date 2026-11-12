from http import HTTPStatus

from tests.unittest_v3.test_users import assert_error, bearer

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"
activity_level_record_id = "test-id"


def test_create_user_activity_level(client, authenticated_user):
    response = client.post(
        "/v3/activity_level/", json={"level": "Active"}, headers=bearer(authenticated_user)
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["level"] == "Active"
    global activity_level_record_id  # noqa: PLW0603
    activity_level_record_id = data["id"]


def test_create_user_activity_level_invalid_level(client, authenticated_user):
    response = client.post(
        "/v3/activity_level/", json={"level": "Super Active"}, headers=bearer(authenticated_user)
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_create_user_activity_level_without_a_session(client, unauthenticated_user):
    response = client.post(
        "/v3/activity_level/", json={"level": "Active"}, headers=bearer(unauthenticated_user)
    )

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_activity_levels_without_token(client):
    assert_error(client.get("/v3/activity_level/"), HTTPStatus.UNAUTHORIZED, "NOT_AUTHENTICATED")


def test_get_user_activity_levels(client, authenticated_user):
    response = client.get("/v3/activity_level/", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) > 0
    assert "level" in data[0]


def test_get_specific_activity_level(client, authenticated_user):
    response = client.get(
        f"/v3/activity_level/{activity_level_record_id}", headers=bearer(authenticated_user)
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["id"] == activity_level_record_id


def test_get_nonexistent_activity_level(client, authenticated_user):
    response = client.get(f"/v3/activity_level/{UNKNOWN_ID}", headers=bearer(authenticated_user))

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")


def test_update_activity_level(client, authenticated_user):
    response = client.put(
        f"/v3/activity_level/{activity_level_record_id}",
        json={"level": "Inactive"},
        headers=bearer(authenticated_user),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["level"] == "Inactive"


def test_update_activity_level_invalid_level(client, authenticated_user):
    response = client.put(
        f"/v3/activity_level/{activity_level_record_id}",
        json={"level": "Super Inactive"},
        headers=bearer(authenticated_user),
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_update_nonexistent_activity_level(client, authenticated_user):
    response = client.put(
        f"/v3/activity_level/{UNKNOWN_ID}",
        json={"level": "Active"},
        headers=bearer(authenticated_user),
    )

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")


def test_update_activity_level_without_a_session(client, unauthenticated_user):
    response = client.put(
        f"/v3/activity_level/{activity_level_record_id}",
        json={"level": "Active"},
        headers=bearer(unauthenticated_user),
    )

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_delete_activity_level(client, authenticated_user):
    response = client.delete(
        f"/v3/activity_level/{activity_level_record_id}", headers=bearer(authenticated_user)
    )

    assert response.status_code == HTTPStatus.NO_CONTENT


def test_delete_nonexistent_activity_level(client, authenticated_user):
    response = client.delete(f"/v3/activity_level/{UNKNOWN_ID}", headers=bearer(authenticated_user))

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")
