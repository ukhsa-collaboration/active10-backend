from http import HTTPStatus

from tests.unittest_v3.test_users import assert_error, bearer


def plan(steps_per_day: int) -> dict:
    return {
        "walking_plan_data": {
            "steps_per_day": steps_per_day,
            "walking_days": 5,
            "walking_hours": 1,
            "walking_minutes": 30,
        }
    }


def test_get_walking_plan_before_creating_one_is_not_found(client, authenticated_user):
    response = client.get("/v3/walking_plans", headers=bearer(authenticated_user))

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")


def test_create_walking_plan(client, authenticated_user):
    response = client.post(
        "/v3/walking_plans", json=plan(10000), headers=bearer(authenticated_user)
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["walking_plan_data"]["steps_per_day"] == 10000  # noqa: PLR2004


def test_create_second_walking_plan_already_exists(client, authenticated_user):
    response = client.post(
        "/v3/walking_plans", json=plan(10000), headers=bearer(authenticated_user)
    )

    assert_error(response, HTTPStatus.BAD_REQUEST, "ALREADY_EXISTS")


def test_create_walking_plan_with_missing_body(client, authenticated_user):
    response = client.post("/v3/walking_plans", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_create_walking_plan_without_a_session(client, unauthenticated_user):
    response = client.post(
        "/v3/walking_plans", json=plan(10000), headers=bearer(unauthenticated_user)
    )

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_walking_plan_without_token(client):
    assert_error(client.get("/v3/walking_plans"), HTTPStatus.UNAUTHORIZED, "NOT_AUTHENTICATED")


def test_get_user_walking_plan(client, authenticated_user):
    response = client.get("/v3/walking_plans", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.OK
    assert response.json()["walking_plan_data"]["steps_per_day"] == 10000  # noqa: PLR2004


def test_get_user_walking_plan_without_a_session(client, unauthenticated_user):
    response = client.get("/v3/walking_plans", headers=bearer(unauthenticated_user))

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_update_walking_plan(client, authenticated_user):
    response = client.put("/v3/walking_plans", json=plan(20000), headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.OK
    assert response.json()["walking_plan_data"]["steps_per_day"] == 20000  # noqa: PLR2004


def test_update_walking_plan_without_a_session(client, unauthenticated_user):
    response = client.put(
        "/v3/walking_plans", json=plan(20000), headers=bearer(unauthenticated_user)
    )

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_delete_walking_plan_without_a_session(client, unauthenticated_user):
    response = client.delete("/v3/walking_plans", headers=bearer(unauthenticated_user))

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_delete_walking_plan(client, authenticated_user):
    response = client.delete("/v3/walking_plans", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.NO_CONTENT


def test_delete_missing_walking_plan_is_not_found(client, authenticated_user):
    response = client.delete("/v3/walking_plans", headers=bearer(authenticated_user))

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")
