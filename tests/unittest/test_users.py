def test_read_user_with_token(client, authenticated_user):
    response = client.get(
        "/v1/users",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["first_name"] == "Default"


def test_read_user_without_token(client):
    response = client.get("/v1/users")
    assert response.status_code == 403


def test_read_user_unauthenticated_token(client, unauthenticated_user):
    response = client.get(
        "/v1/users",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
