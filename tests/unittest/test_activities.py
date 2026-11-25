import time
from datetime import datetime
from unittest.mock import patch

import pytest

from crud.activities_crud import create_activity
from schemas.activity import UserActivityRequestSchema
from service.activity_service import load_activities_data_in_sns
from tests.unittest.conftest import override_get_db_context_session, user_uuid_pk
from utils.background_jobs import run_tracked_job

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
        patch("service.background_job_service.create_job", return_value="job-123"),
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

        assert response.status_code == 202  # noqa: PLR2004
        resp = response.json()
        assert resp["job_id"] == "job-123"
        assert resp["status"] == "started"
        assert resp["status_url"].endswith("/v1/activities/job-123/status")
        assert response.headers["location"].endswith("/v1/activities/job-123/status")

        mock_add_task.assert_called_once()
        args, _kwargs = mock_add_task.call_args
        assert args[0] == run_tracked_job
        assert args[1] == "job-123"
        assert args[2] == load_activities_data_in_sns
        assert str(args[4]) == str(user_uuid_pk)


def test_create_activities_without_rewards(client, authenticated_user, db_session):
    with (
        patch("fastapi.BackgroundTasks.add_task") as mock_add_task,
        patch("service.background_job_service.create_job", return_value="job-123"),
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

        assert response.status_code == 202  # noqa: PLR2004
        resp = response.json()
        assert resp["job_id"] == "job-123"
        assert resp["status"] == "started"
        assert resp["status_url"].endswith("/v1/activities/job-123/status")
        assert response.headers["location"].endswith("/v1/activities/job-123/status")

        mock_add_task.assert_called_once()
        args, _kwargs = mock_add_task.call_args
        assert args[0] == run_tracked_job
        assert args[1] == "job-123"
        assert args[2] == load_activities_data_in_sns
        assert str(args[4]) == str(user_uuid_pk)


def test_get_activity_job_status_returns_started(client, authenticated_user):
    with patch(
        "service.background_job_service.get_job",
        return_value={
            "status": "started",
            "user_id": str(authenticated_user.id),
            "created_at": 123,
            "updated_at": 123,
        },
    ):
        response = client.get(
            "/v1/activities/job-123/status",
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 200  # noqa: PLR2004
    assert response.json() == {
        "job_id": "job-123",
        "status": "started",
        "created_at": 123,
        "updated_at": 123,
    }


def test_get_activity_job_status_owner_only(client, authenticated_user):
    with patch(
        "service.background_job_service.get_job",
        return_value={
            "status": "started",
            "user_id": "some-other-user",
            "created_at": 123,
            "updated_at": 123,
        },
    ):
        response = client.get(
            "/v1/activities/job-123/status",
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 404  # noqa: PLR2004
    assert response.json() == {"detail": "Job not found"}


def test_get_activity_job_status_not_found(client, authenticated_user):
    with patch("service.background_job_service.get_job", return_value=None):
        response = client.get(
            "/v1/activities/job-123/status",
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 404  # noqa: PLR2004
    assert response.json() == {"detail": "Job not found"}


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
