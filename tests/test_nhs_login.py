def test_nhs_login_redirect(client):
    response = client.get("/nhs_login/test_app/12345", follow_redirects=False)

    assert response.status_code == 307
    assert "https://auth.aos.signin.nhs.uk/authorize?" in response.headers["location"]


def test_nhs_login_missing_app_internal_id(client):
    response = client.get(
        "/nhs_login/test_app/",
        follow_redirects=False
    )

    assert response.status_code == 404


def test_nhs_login_callback_success(client):
    response = client.get(
        "/nhs_login/callback",
        params={"code": "123", "state": "test_app_12345"},
        follow_redirects=False
    )

    assert response.status_code == 307
    assert response.headers["location"] == "active10dev://nhs_login_callback?code=123&state=test_app_12345"


def test_nhs_login_callback_missing_code(client):
    response = client.get(
        "/nhs_login/callback",
        params={"state": "test_app_12345"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Missing code"}


def test_nhs_login_callback_missing_state(client):
    response = client.get(
        "/nhs_login/callback",
        params={"code": "123"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Missing state"}


def test_nhs_login_callback_empty_query_params(client):
    response = client.get("/nhs_login/callback", follow_redirects=False, params={})

    assert response.status_code == 400
    assert response.json() == {"detail": "Missing state and code"}


def test_logout_user_without_token(client):
    response = client.post("/nhs_login/logout")
    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


def test_logout_with_unauthenticated_user(client, unauthenticated_user):

    response = client.post(
        "/nhs_login/logout",
        headers = {"Authorization": f"Bearer {unauthenticated_user.token.token}"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_logout_with_authenticated_user(client, authenticated_user):

    response = client.post(
        "/nhs_login/logout",
        headers = {"Authorization": f"Bearer {authenticated_user.token.token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"message": "User logged out successfully"}


from tests.conftest import unauthenticated_user, authenticated_user


def test_disconnect_with_unauthenticated_user(client, unauthenticated_user):
    response = client.post(
        "/nhs_login/disconnect",
        headers = {"Authorization": f"Bearer {unauthenticated_user.token.token}"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_disconnect_user_without_token(client):
    response = client.post("/nhs_login/disconnect")

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


def test_disconnect_user_with_authenticated_user(client, authenticated_user):
    response = client.post(
        "/nhs_login/disconnect",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"message": "User disconnected successfully"}
