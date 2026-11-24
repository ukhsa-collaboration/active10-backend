import time
from contextlib import contextmanager
from datetime import datetime
from http import HTTPStatus
from unittest.mock import patch

import pytest

from crud.activities_crud import create_activity
from schemas.activity import UserActivityRequestSchema
from service.activity_service import load_activities_data_in_sns
from tests.unittest_v3.test_users import assert_error, bearer

ONE_DAY = 86400
current_timestamp = int(datetime.now().timestamp())
activity_payload = {
    "date": current_timestamp,
    "user_postcode": "HD81",
    "user_age_range": "23-39",
    "rewards": [{"earned": 63, "slug": "high_five"}],
    "activity": {"brisk_minutes": 109, "walking_minutes": 30, "steps": 1867},
}


@contextmanager
def same_session(db_session):
    yield db_session


@pytest.fixture
def stored_activity(authenticated_user, db_session):
    with patch("crud.activities_crud.get_db_context_session", lambda: same_session(db_session)):
        payload = UserActivityRequestSchema(**{**activity_payload, "date": int(time.time())})
        create_activity(activity_payload=payload, user_id=authenticated_user.id)


@pytest.mark.parametrize("payload", [activity_payload, {**activity_payload, "rewards": None}])
def test_create_activity_is_published_in_the_background(client, authenticated_user, payload):
    payload = {key: value for key, value in payload.items() if value is not None}
    with patch("fastapi.BackgroundTasks.add_task") as add_task:
        response = client.post("/v3/activities", json=payload, headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {"message": "Success"}
    args, _ = add_task.call_args
    assert args[0] is load_activities_data_in_sns
    assert args[2] == authenticated_user.id


@pytest.mark.parametrize(
    "payload",
    [
        {key: value for key, value in activity_payload.items() if key != "date"},
        {**activity_payload, "activity": {"brisk_minutes": "ten", "steps": 1}},
    ],
    ids=["missing-field", "wrong-type"],
)
def test_create_activity_with_an_invalid_body(client, authenticated_user, payload):
    response = client.post("/v3/activities", json=payload, headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


def test_create_activity_without_a_session(client, unauthenticated_user):
    response = client.post(
        "/v3/activities", json=activity_payload, headers=bearer(unauthenticated_user)
    )

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_activities_without_token(client):
    assert_error(client.get("/v3/activities"), HTTPStatus.UNAUTHORIZED, "NOT_AUTHENTICATED")


def test_list_activities(client, authenticated_user, db_session, stored_activity):
    with patch("crud.activities_crud.get_db_context_session", lambda: same_session(db_session)):
        response = client.get("/v3/activities", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.OK
    assert "id" in response.json()[0]


def test_list_activities_in_a_date_range(client, authenticated_user, db_session, stored_activity):
    params = {"start_date": current_timestamp - ONE_DAY, "end_date": current_timestamp + ONE_DAY}

    with patch("crud.activities_crud.get_db_context_session", lambda: same_session(db_session)):
        response = client.get("/v3/activities", params=params, headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) >= 1


def test_list_activities_with_no_match_is_not_found(client, authenticated_user, db_session):
    with patch("crud.activities_crud.get_db_context_session", lambda: same_session(db_session)):
        response = client.get(
            "/v3/activities", params={"date": 1}, headers=bearer(authenticated_user)
        )

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")


@pytest.mark.parametrize(
    "params",
    [
        {"date": current_timestamp, "start_date": current_timestamp},
        {"start_date": current_timestamp},
        {"start_date": current_timestamp, "end_date": current_timestamp - ONE_DAY},
        {"start_date": current_timestamp - 400 * ONE_DAY, "end_date": current_timestamp},
    ],
    ids=["date-with-range", "start-without-end", "start-after-end", "longer-than-a-year"],
)
def test_list_activities_with_invalid_filters(client, authenticated_user, params):
    response = client.get("/v3/activities", params=params, headers=bearer(authenticated_user))

    assert_error(response, HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")


def test_list_activities_without_a_session(client, unauthenticated_user):
    response = client.get("/v3/activities", headers=bearer(unauthenticated_user))

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def wheeling(**scores) -> dict:
    return {
        **activity_payload,
        "activity": {"brisk_minutes": 20, "walking_minutes": 30, "steps": 0, **scores},
    }


@pytest.mark.parametrize(
    ("scores", "published"),
    [
        ({"effort": 7, "feeling": 2}, (7, 2)),
        ({}, (None, None)),
        ({"feeling": 2}, (None, None)),
    ],
    ids=["wheeling", "walking", "feeling-without-effort"],
)
def test_create_activity_publishes_effort_and_feeling(
    client, authenticated_user, scores, published
):
    with patch("fastapi.BackgroundTasks.add_task") as add_task:
        response = client.post(
            "/v3/activities", json=wheeling(**scores), headers=bearer(authenticated_user)
        )

    assert response.status_code == HTTPStatus.CREATED
    args, _ = add_task.call_args
    assert (args[1].activity.effort, args[1].activity.feeling) == published


@pytest.mark.parametrize(
    "scores", [{"effort": 0}, {"effort": 11}, {"feeling": -1}, {"effort": 5, "feeling": 3}]
)
def test_create_activity_with_out_of_range_effort_or_feeling(client, authenticated_user, scores):
    response = client.post(
        "/v3/activities", json=wheeling(**scores), headers=bearer(authenticated_user)
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_list_activities_returns_effort_and_feeling(client, authenticated_user, db_session):
    walking_date, wheeling_date = current_timestamp - 200, current_timestamp - 100

    with patch("crud.activities_crud.get_db_context_session", lambda: same_session(db_session)):
        for date, scores in [(walking_date, {}), (wheeling_date, {"effort": 4, "feeling": 0})]:
            payload = UserActivityRequestSchema(**{**wheeling(**scores), "date": date})
            create_activity(activity_payload=payload, user_id=authenticated_user.id)

        walking = client.get(
            "/v3/activities", params={"date": walking_date}, headers=bearer(authenticated_user)
        )
        wheeled = client.get(
            "/v3/activities", params={"date": wheeling_date}, headers=bearer(authenticated_user)
        )

    assert (walking.json()[0]["effort"], walking.json()[0]["feeling"]) == (None, None)
    assert (wheeled.json()[0]["effort"], wheeled.json()[0]["feeling"]) == (4, 0)
