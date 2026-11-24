def test_read_user_with_token(client, authenticated_user):
    response = client.get(
        "/v1/users",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()

    assert data["first_name"] == "Default"
    assert data["activity_type"] == "walking"


def test_read_user_without_token(client):
    response = client.get("/v1/users")
    assert response.status_code == 403  # noqa: PLR2004
    assert response.json() == {"detail": "Not authenticated"}


def test_read_user_with_a_basic_header(client):
    response = client.get("/v1/users", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert response.status_code == 403  # noqa: PLR2004
    assert response.json() == {"detail": "Not authenticated"}


def test_read_user_unauthenticated_token(client, unauthenticated_user):
    response = client.get(
        "/v1/users",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )
    assert response.status_code == 404  # noqa: PLR2004
    assert response.json() == {"detail": "User not found"}


def test_update_activity_type(client, authenticated_user):
    headers = {"Authorization": f"Bearer {authenticated_user.token.token}"}

    response = client.patch("/v1/users/", json={"activity_type": "wheeling"}, headers=headers)
    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert data["activity_type"] == "wheeling"
    assert data["first_name"] == "Default"
    assert data == client.get("/v1/users", headers=headers).json()

    response = client.patch("/v1/users/", json={"activity_type": "walking"}, headers=headers)
    assert response.json()["activity_type"] == "walking"


def test_update_activity_type_invalid_value(client, authenticated_user):
    response = client.patch(
        "/v1/users/",
        json={"activity_type": "running"},
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )
    assert response.status_code == 422  # noqa: PLR2004


def test_update_activity_type_missing_value(client, authenticated_user):
    response = client.patch(
        "/v1/users/",
        json={},
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )
    assert response.status_code == 422  # noqa: PLR2004


def test_update_activity_type_without_token(client):
    response = client.patch("/v1/users/", json={"activity_type": "wheeling"})
    assert response.status_code == 403  # noqa: PLR2004


def test_update_activity_type_unauthenticated(client, unauthenticated_user):
    response = client.patch(
        "/v1/users/",
        json={"activity_type": "wheeling"},
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )
    assert response.status_code == 404  # noqa: PLR2004
