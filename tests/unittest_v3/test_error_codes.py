from http import HTTPStatus

from fastapi.testclient import TestClient

from main import app


def test_legacy_error_response_unchanged():
    client = TestClient(app)

    response = client.post("/nhs_login/logout")

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {"detail": "Not authenticated"}
    assert "www-authenticate" not in response.headers
