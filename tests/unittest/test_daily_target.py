from uuid import uuid4

from tests.unittest.conftest import authenticated_user, unauthenticated_user  # noqa

target_id = None
invalid_target_id = uuid4()


def test_create_daily_target(client, authenticated_user):  # noqa
    payload = {"daily_target": 20, "date": 12341234}
    response = client.post(
        "/v1/daily_targets",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 201  # noqa: PLR2004
    data = response.json()
    global target_id  # noqa: PLW0603
    target_id = data["id"]
    assert data["daily_target"] == 20  # noqa: PLR2004


def test_create_daily_target_with_missing_body(client, authenticated_user):  # noqa
    response = client.post(
        "/v1/daily_targets",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422  # noqa: PLR2004


def test_create_daily_target_by_unauthenticated_user(client, unauthenticated_user):  # noqa
    payload = {"daily_target": 20, "date": 12341234}
    response = client.post(
        "/v1/daily_targets",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_get_user_all_daily_targets_by_unauthenticated_user(
    client,
    unauthenticated_user,  # noqa
):
    response = client.get(
        "/v1/daily_targets/",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_get_user_all_daily_target(client, authenticated_user):  # noqa: F811
    response = client.get(
        "/v1/daily_targets/",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert len(data) > 0


def test_get_user_single_daily_target(client, authenticated_user):  # noqa
    global target_id  # noqa: PLW0602

    response = client.get(
        f"/v1/daily_targets/{target_id}",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert data["id"] == target_id


def test_get_user_single_invalid_daily_target(client, authenticated_user):  # noqa
    global invalid_target_id  # noqa: PLW0602

    response = client.get(
        f"/v1/daily_targets/{invalid_target_id}",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_update_daily_target(client, authenticated_user):  # noqa
    global target_id  # noqa: PLW0602
    payload = {"date": 123499, "daily_target": 10}
    response = client.put(
        f"/v1/daily_targets/{target_id}",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert data["daily_target"] == 10  # noqa: PLR2004


def test_update_daily_target_by_unauthenticated_user(client, unauthenticated_user):  # noqa
    global target_id  # noqa: PLW0602

    payload = {"daily_target": 20, "date": 12341234}

    response = client.put(
        f"/v1/daily_targets/{target_id}",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_delete_daily_target_by_unauthenticated_user(client, unauthenticated_user):  # noqa
    global target_id  # noqa: PLW0602

    response = client.delete(
        f"/v1/daily_targets/{target_id}",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_delete_daily_target(client, authenticated_user):  # noqa
    global target_id  # noqa: PLW0602

    response = client.delete(
        f"/v1/daily_targets/{target_id}",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 204  # noqa: PLR2004


def test_delete_invalid_daily_target(client, authenticated_user):  # noqa
    global invalid_target_id  # noqa: PLW0602

    response = client.delete(
        f"/v1/daily_targets/{invalid_target_id}",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004
