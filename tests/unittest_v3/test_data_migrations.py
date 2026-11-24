from http import HTTPStatus
from unittest.mock import patch

import pytest

from service.migrations_service import publish_bulk_activities_data_to_sns
from tests.unittest_v3.test_users import assert_error, bearer

MONTH = 1714637586


def activity(date: int, **scores) -> dict:
    return {
        "date": date,
        "user_postcode": "HD81",
        "user_age_range": "23-39",
        "rewards": [{"earned": 63, "slug": "high_five"}],
        "activity": {"brisk_minutes": 109, "walking_minutes": 30, "steps": 1867, **scores},
    }


def test_bulk_activities_are_published_in_the_background(client, authenticated_user):
    payload = {"month": MONTH, "activities": [activity(MONTH)]}

    with patch("fastapi.BackgroundTasks.add_task") as add_task:
        response = client.post(
            "/v3/migrations/activities", json=payload, headers=bearer(authenticated_user)
        )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {"message": "Success"}
    args, _ = add_task.call_args
    assert args[0] is publish_bulk_activities_data_to_sns
    assert args[2] == authenticated_user.id


def test_activities_outside_the_month_are_rejected(client, authenticated_user):
    payload = {"month": MONTH, "activities": [activity(MONTH), activity(1717229586)]}

    with patch("fastapi.BackgroundTasks.add_task") as add_task:
        response = client.post(
            "/v3/migrations/activities", json=payload, headers=bearer(authenticated_user)
        )

    assert_error(response, HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
    add_task.assert_not_called()


def test_empty_activities_is_a_validation_error(client, authenticated_user):
    response = client.post(
        "/v3/migrations/activities",
        json={"month": MONTH, "activities": []},
        headers=bearer(authenticated_user),
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


def test_missing_month_is_a_validation_error(client, authenticated_user):
    response = client.post(
        "/v3/migrations/activities",
        json={"activities": [activity(MONTH)]},
        headers=bearer(authenticated_user),
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT


def test_bulk_activities_without_a_session(client, unauthenticated_user):
    response = client.post(
        "/v3/migrations/activities",
        json={"month": MONTH, "activities": [activity(MONTH)]},
        headers=bearer(unauthenticated_user),
    )

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_bulk_activities_publish_effort_and_feeling(client, authenticated_user):
    activities = [activity(MONTH, effort=10, feeling=1), activity(MONTH, feeling=2)]

    with patch("fastapi.BackgroundTasks.add_task") as add_task:
        response = client.post(
            "/v3/migrations/activities",
            json={"month": MONTH, "activities": activities},
            headers=bearer(authenticated_user),
        )

    assert response.status_code == HTTPStatus.CREATED
    args, _ = add_task.call_args
    published = [(a.activity.effort, a.activity.feeling) for a in args[1].activities]
    assert published == [(10, 1), (None, None)]


@pytest.mark.parametrize("scores", [{"effort": 0}, {"effort": 11}, {"effort": 5, "feeling": 3}])
def test_bulk_activities_with_out_of_range_effort_or_feeling(client, authenticated_user, scores):
    with patch("fastapi.BackgroundTasks.add_task") as add_task:
        response = client.post(
            "/v3/migrations/activities",
            json={"month": MONTH, "activities": [activity(MONTH, **scores)]},
            headers=bearer(authenticated_user),
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    add_task.assert_not_called()
