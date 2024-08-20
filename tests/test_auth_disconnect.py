from tests.conftest import unauthenticated_user, authenticated_user


def test_disconnect_with_unauthenticated_user(client, unauthenticated_user):
    response = client.get(
        "/v1/auth/disconnect/",
        headers = {"Authorization": f"Bearer {unauthenticated_user.token.token}"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_disconnect_user_without_token(client):
    response = client.get("/v1/auth/disconnect/")

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


def test_disconnect_user_with_authenticated_user(client, authenticated_user):
    response = client.get(
        "/v1/auth/disconnect/",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"message": "User disconnected successfully"}
