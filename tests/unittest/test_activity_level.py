activity_level_record_id = "test-id"


def test_create_user_activity_level(client, authenticated_user):
    payload = {
        "level": "Active",
    }

    response = client.post(
        "/v1/activity_level/",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert data["level"] == "Active"

    global activity_level_record_id  # noqa: PLW0603
    activity_level_record_id = data["id"]


def test_create_user_activity_level_invalid_level(client, authenticated_user):
    payload = {
        "level": "Super Active",
    }

    response = client.post(
        "/v1/activity_level/",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422  # noqa: PLR2004


def test_create_user_activity_level_unauthenticated(client, unauthenticated_user):
    payload = {
        "level": "Active",
    }

    response = client.post(
        "/v1/activity_level/",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_get_user_activity_levels(client, authenticated_user):
    response = client.get(
        "/v1/activity_level/",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert type(data) == list  # noqa: E721
    assert len(data) > 0
    assert "level" in data[0]


def test_get_specific_activity_level(client, authenticated_user):
    response = client.get(
        f"/v1/activity_level/{activity_level_record_id}",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert data["id"] == activity_level_record_id
    assert "level" in data


def test_get_nonexistent_activity_level(client, authenticated_user):
    response = client.get(
        "/v1/activity_level/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_update_activity_level(client, authenticated_user):
    payload = {
        "level": "Inactive",
    }

    response = client.put(
        f"/v1/activity_level/{activity_level_record_id}",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert data["level"] == "Inactive"


def test_update_activity_level_invalid_level(client, authenticated_user):
    payload = {
        "level": "Super Inactive",
    }

    response = client.put(
        f"/v1/activity_level/{activity_level_record_id}",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422  # noqa: PLR2004


def test_update_nonexistent_activity_level(client, authenticated_user):
    payload = {
        "level": "Active",
    }

    response = client.put(
        "/v1/activity_level/00000000-0000-0000-0000-000000000000",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_update_activity_level_unauthenticated(client, unauthenticated_user):
    payload = {"level": "Active", "date": 1677649420}

    response = client.put(
        f"/v1/activity_level/{activity_level_record_id}",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_delete_activity_level_authenticated_user(client, authenticated_user):
    response = client.delete(
        f"/v1/activity_level/{activity_level_record_id}",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 204  # noqa: PLR2004
