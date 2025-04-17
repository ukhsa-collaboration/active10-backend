activity_level_record_id = "test-id"


def test_create_user_activity_level(client, authenticated_user):
    payload = {
        "level": "Active",
        "date": 1677649420
    }

    response = client.post(
        "/v1/activity_level/",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "Active"
    assert data["date"] == 1677649420

    global activity_level_record_id
    activity_level_record_id = data["id"]


def test_create_user_activity_level_invalid_level(client, authenticated_user):
    payload = {
        "level": "Super Active",  # Invalid level
        "date": 1677649420
    }

    response = client.post(
        "/v1/activity_level/",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 400


def test_create_user_activity_level_without_date(client, authenticated_user):
    payload = {
        "level": "Moderately active"
    }

    response = client.post(
        "/v1/activity_level/",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "Moderately active"
    assert "date" in data


def test_create_user_activity_level_unauthenticated(client, unauthenticated_user):
    payload = {
        "level": "Active",
        "date": 1677649420
    }

    response = client.post(
        "/v1/activity_level/",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404


def test_get_user_activity_levels(client, authenticated_user):
    response = client.get(
        "/v1/activity_level/",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert type(data) == list
    assert len(data) > 0
    assert "level" in data[0]
    assert "date" in data[0]


def test_get_specific_activity_level(client, authenticated_user):
    response = client.get(
        f"/v1/activity_level/{activity_level_record_id}",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == activity_level_record_id
    assert "level" in data
    assert "date" in data


def test_get_nonexistent_activity_level(client, authenticated_user):
    response = client.get(
        f"/v1/activity_level/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 404


def test_update_activity_level(client, authenticated_user):
    payload = {
        "level": "Inactive",
        "date": 1677649420
    }

    response = client.put(
        f"/v1/activity_level/{activity_level_record_id}",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "Inactive"
    assert data["date"] == 1677649420


def test_update_activity_level_invalid_level(client, authenticated_user):
    payload = {
        "level": "Super Inactive",  # Invalid level
        "date": 1677649420
    }

    response = client.put(
        f"/v1/activity_level/{activity_level_record_id}",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 400


def test_update_nonexistent_activity_level(client, authenticated_user):
    payload = {
        "level": "Active",
        "date": 1677649420
    }

    response = client.put(
        f"/v1/activity_level/00000000-0000-0000-0000-000000000000",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 404


def test_update_activity_level_unauthenticated(client, unauthenticated_user):
    payload = {
        "level": "Active",
        "date": 1677649420
    }

    response = client.put(
        f"/v1/activity_level/{activity_level_record_id}",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404
