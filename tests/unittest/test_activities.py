import time
from datetime import datetime
from unittest.mock import patch

import pytest

from crud.activities_crud import create_activity
from schemas.activity import UserActivityRequestSchema
from service.activity_service import load_activities_data_in_sns
from tests.unittest.conftest import override_get_db_context_session, user_uuid_pk

current_timestamp = int(datetime.now().timestamp())


@pytest.fixture
def add_activity(authenticated_user, db_session):
    with patch(
        "crud.activities_crud.get_db_context_session",
        lambda: override_get_db_context_session(db_session),
    ):
        activity_payload = UserActivityRequestSchema(
            date=int(time.time()),
            user_postcode="HD81",
            user_age_range="23-39",
            rewards=[{"earned": 63, "slug": "high_five"}],
            activity={"brisk_minutes": 109, "walking_minutes": 30, "steps": 1867},
        )
        activity = create_activity(activity_payload=activity_payload, user_id=authenticated_user.id)
        assert activity.id is not None


def test_create_activities(client, authenticated_user, db_session):
    with (
        patch("fastapi.BackgroundTasks.add_task") as mock_add_task,
        patch(
            "crud.activities_crud.get_db_context_session",
            lambda: override_get_db_context_session(db_session),
        ),
    ):
        activity_payload = {
            "date": current_timestamp,
            "user_postcode": "HD81",
            "user_age_range": "23-39",
            "rewards": [{"earned": 63, "slug": "high_five"}],
            "activity": {"brisk_minutes": 109, "walking_minutes": 30, "steps": 1867},
        }

        response = client.post(
            "/v1/activities",
            json=activity_payload,
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

        assert response.status_code == 201  # noqa: PLR2004
        resp = response.json()
        assert resp["message"] == "Success"

        mock_add_task.assert_called_once()
        args, _kwargs = mock_add_task.call_args
        assert args[0] == load_activities_data_in_sns
        assert str(args[2]) == str(user_uuid_pk)


def test_create_activities_without_rewards(client, authenticated_user, db_session):
    with (
        patch("fastapi.BackgroundTasks.add_task") as mock_add_task,
        patch(
            "crud.activities_crud.get_db_context_session",
            lambda: override_get_db_context_session(db_session),
        ),
    ):
        activity_payload = {
            "date": current_timestamp,
            "user_postcode": "HD81",
            "user_age_range": "23-39",
            "activity": {"brisk_minutes": 109, "walking_minutes": 30, "steps": 1867},
        }

        response = client.post(
            "/v1/activities",
            json=activity_payload,
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

        assert response.status_code == 201  # noqa: PLR2004
        resp = response.json()
        assert resp["message"] == "Success"

        mock_add_task.assert_called_once()
        args, _kwargs = mock_add_task.call_args
        assert args[0] == load_activities_data_in_sns
        assert str(args[2]) == str(user_uuid_pk)


def test_create_activities_missing_fields(client, authenticated_user):
    activity_payload = {
        "user_postcode": "HD81",
        "user_age_range": "23-39",
        "rewards": [{"earned": 63, "slug": "high_five"}],
        "activity": {"brisk_minutes": 109, "steps": 1867},
    }

    response = client.post(
        "/v1/activities",
        json=activity_payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422  # noqa: PLR2004


def test_create_activities_invalid_data_types(client, authenticated_user):
    activity_payload = {
        "date": datetime.now().isoformat(),
        "user_postcode": "HD81",
        "user_age_range": "23-39",
        "rewards": [{"earned": 63, "slug": "high_five"}],
        "activity": {"brisk_minutes": "ten", "walking_minutes": 30, "steps": 1867},
    }

    response = client.post(
        "/v1/activities",
        json=activity_payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422  # noqa: PLR2004


def test_list_activities(client, authenticated_user, db_session, add_activity):
    with patch(
        "crud.activities_crud.get_db_context_session",
        lambda: override_get_db_context_session(db_session),
    ):
        response = client.get(
            "/v1/activities",
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

        assert response.status_code == 200  # noqa: PLR2004
        response_data = response.json()
        assert "id" in response_data[0]
        assert response.status_code == 200  # noqa: PLR2004
        response_data = response.json()
        assert "id" in response_data[0]


def test_list_activities_by_unauthenticated_user(client, unauthenticated_user):
    response = client.get(
        "/v1/activities",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_create_activities_with_effort_and_feeling(client, authenticated_user):
    activity_payload = {
        "date": current_timestamp,
        "user_postcode": "HD81",
        "user_age_range": "23-39",
        "activity": {
            "brisk_minutes": 20,
            "walking_minutes": 30,
            "steps": 0,
            "effort": 7,
            "feeling": 2,
        },
    }

    with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        response = client.post(
            "/v1/activities",
            json=activity_payload,
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 201  # noqa: PLR2004
    args, _kwargs = mock_add_task.call_args
    assert args[1].activity.effort == 7  # noqa: PLR2004
    assert args[1].activity.feeling == 2  # noqa: PLR2004


def test_create_activities_without_effort_and_feeling_publishes_nulls(client, authenticated_user):
    activity_payload = {
        "date": current_timestamp,
        "user_postcode": "HD81",
        "user_age_range": "23-39",
        "activity": {"brisk_minutes": 109, "walking_minutes": 30, "steps": 1867},
    }

    with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        response = client.post(
            "/v1/activities",
            json=activity_payload,
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 201  # noqa: PLR2004
    args, _kwargs = mock_add_task.call_args
    published = args[1].model_dump()["activity"]
    assert published["effort"] is None
    assert published["feeling"] is None


@pytest.mark.parametrize("scores", [{"feeling": 2}, {"effort": None, "feeling": 1}])
def test_create_activities_with_feeling_but_no_effort_clears_feeling(
    client, authenticated_user, scores
):
    activity_payload = {
        "date": current_timestamp,
        "user_postcode": "HD81",
        "user_age_range": "23-39",
        "activity": {"brisk_minutes": 10, "walking_minutes": 20, "steps": 3000, **scores},
    }

    with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        response = client.post(
            "/v1/activities",
            json=activity_payload,
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 201  # noqa: PLR2004
    args, _kwargs = mock_add_task.call_args
    published = args[1].model_dump()["activity"]
    assert published["effort"] is None
    assert published["feeling"] is None


@pytest.mark.parametrize(
    "scores",
    [{"effort": 0}, {"effort": 11}, {"feeling": -1}, {"feeling": 3}, {"effort": "high"}],
)
def test_create_activities_with_out_of_range_effort_or_feeling(client, authenticated_user, scores):
    activity_payload = {
        "date": current_timestamp,
        "user_postcode": "HD81",
        "user_age_range": "23-39",
        "activity": {"brisk_minutes": 20, "walking_minutes": 30, "steps": 0, **scores},
    }

    response = client.post(
        "/v1/activities",
        json=activity_payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422  # noqa: PLR2004


def test_list_activities_returns_effort_and_feeling(client, authenticated_user, db_session):
    walking_date = current_timestamp - 200
    wheeling_date = current_timestamp - 100

    with patch(
        "crud.activities_crud.get_db_context_session",
        lambda: override_get_db_context_session(db_session),
    ):
        for date, scores in [(walking_date, {}), (wheeling_date, {"effort": 4, "feeling": 0})]:
            create_activity(
                activity_payload=UserActivityRequestSchema(
                    date=date,
                    user_postcode="HD81",
                    user_age_range="23-39",
                    activity={"brisk_minutes": 5, "walking_minutes": 10, "steps": 0, **scores},
                ),
                user_id=authenticated_user.id,
            )

        headers = {"Authorization": f"Bearer {authenticated_user.token.token}"}
        walking = client.get(f"/v1/activities?date={walking_date}", headers=headers).json()
        wheeling = client.get(f"/v1/activities?date={wheeling_date}", headers=headers).json()

    assert walking[0]["effort"] is None
    assert walking[0]["feeling"] is None
    assert wheeling[0]["effort"] == 4  # noqa: PLR2004
    assert wheeling[0]["feeling"] == 0
