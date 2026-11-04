from http import HTTPStatus

from auth.jwt_handler import sign_jwt


def bearer(user) -> dict:
    return {"Authorization": f"Bearer {user.access_token}"}


def assert_error(response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


def test_read_user_with_token(client, authenticated_user):
    response = client.get("/v3/users/", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.OK
    assert response.json()["first_name"] == "Default"


def test_read_user_without_token(client):
    assert_error(client.get("/v3/users/"), HTTPStatus.UNAUTHORIZED, "NOT_AUTHENTICATED")


def test_read_user_without_a_session(client, unauthenticated_user):
    response = client.get("/v3/users/", headers=bearer(unauthenticated_user))

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_legacy_nhs_login_token_is_rejected(client, authenticated_user):
    legacy = {"Authorization": f"Bearer {sign_jwt(str(authenticated_user.id))}"}

    assert_error(client.get("/v3/users/", headers=legacy), HTTPStatus.UNAUTHORIZED, "TOKEN_INVALID")


def test_email_preferences_subscribe_and_unsubscribe(client, authenticated_user):
    body = {"name": "active10_mailing_list"}
    unsubscribe = "/v3/users/email_preferences/unsubscribe"
    subscribe = "/v3/users/email_preferences/subscribe"

    not_subscribed = client.post(unsubscribe, json=body, headers=bearer(authenticated_user))
    assert_error(not_subscribed, HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")

    response = client.post(subscribe, json=body, headers=bearer(authenticated_user))
    assert response.json() == {"message": "Subscribed to email preferences"}

    again = client.post(subscribe, json=body, headers=bearer(authenticated_user))
    assert_error(again, HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")

    response = client.post(unsubscribe, json=body, headers=bearer(authenticated_user))
    assert response.json() == {"message": "Unsubscribed from email preferences"}

    again = client.post(unsubscribe, json=body, headers=bearer(authenticated_user))
    assert_error(again, HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")

    resubscribed = client.post(subscribe, json=body, headers=bearer(authenticated_user))
    assert resubscribed.status_code == HTTPStatus.OK


def test_email_preference_with_an_unknown_list_is_a_validation_error(client, authenticated_user):
    response = client.post(
        "/v3/users/email_preferences/subscribe",
        json={"name": "another_list"},
        headers=bearer(authenticated_user),
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_email_preferences_without_a_session(client, unauthenticated_user):
    response = client.post(
        "/v3/users/email_preferences/subscribe",
        json={"name": "active10_mailing_list"},
        headers=bearer(unauthenticated_user),
    )

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")
