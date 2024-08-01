from tests.conftest import authenticated_user_token, unauthenticated_user_token


def test_read_user_with_token(client):
    token = authenticated_user_token()
    response = client.get("/v1/users/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()

    assert data["unique_id"] == "3a8d2869-0b2e-485a-9e67-8a906e6194ce"
    assert data["first_name"] == "Default"
    assert data["email"] == "default@example.com"


def test_read_user_without_token(client):
    response = client.get("/v1/users/")
    assert response.status_code == 403


def test_read_user_fake_token(client):
    fake_token = unauthenticated_user_token()
    response = client.get("/v1/users/", headers={"Authorization": f"Bearer {fake_token}"})
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_read_user_with_invalid_token(client):
    response = client.get("/v1/users/", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 403
