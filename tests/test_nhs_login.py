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
