from unittest.mock import patch

from tests.unittest.conftest import override_get_db_context_session
from utils.background_jobs import run_tracked_job


def test_post_activities_migrations(client, authenticated_user, db_session):
    with (
        patch("fastapi.BackgroundTasks.add_task") as mock_add_task,
        patch("service.background_job_service.create_job", return_value="job-123"),
        patch(
            "crud.activities_crud.get_db_context_session",
            lambda: override_get_db_context_session(db_session),
        ),
    ):
        activity_migration_payload = {
            "month": 1714637586,
            "activities": [
                {
                    "date": 1714637586,
                    "user_postcode": "HD81",
                    "user_age_range": "23-39",
                    "rewards": [{"earned": 63, "slug": "high_five"}],
                    "activity": {
                        "brisk_minutes": 109,
                        "walking_minutes": 30,
                        "steps": 1867,
                    },
                }
            ],
        }

        response = client.post(
            "/v1/migrations/activities",
            json=activity_migration_payload,
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

        assert response.status_code == 202  # noqa: PLR2004
        created_data = response.json()
        assert created_data["job_id"] == "job-123"
        assert created_data["status"] == "started"
        assert created_data["status_url"].endswith("/v1/migrations/activities/job-123/status")
        assert response.headers["location"].endswith("/v1/migrations/activities/job-123/status")

        mock_add_task.assert_called_once()
        args, _kwargs = mock_add_task.call_args
        assert args[0] == run_tracked_job
        assert args[1] == "job-123"


def test_post_activities_migrations_with_out_of_range_activities(client, authenticated_user):
    activity_migration_payload = {
        "month": 1714637586,
        "activities": [
            {
                "date": 1714637586,
                "user_postcode": "HD81",
                "user_age_range": "23-39",
                "rewards": [{"earned": 63, "slug": "high_five"}],
                "activity": {
                    "brisk_minutes": 109,
                    "walking_minutes": 30,
                    "steps": 1867,
                },
            },
            {
                "date": 1717229586,
                "user_postcode": "HD82",
                "user_age_range": "23-39",
                "rewards": [{"earned": 100, "slug": "gold_star"}],
                "activity": {
                    "brisk_minutes": 200,
                    "walking_minutes": 50,
                    "steps": 3000,
                },
            },
        ],
    }

    response = client.post(
        "/v1/migrations/activities",
        json=activity_migration_payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 400  # noqa: PLR2004
    assert response.json() == {"detail": "Some activities are out of the month range"}


def test_post_activities_migrations_with_empty_activities(client, authenticated_user):
    activity_migration_payload = {"month": 1714637586, "activities": []}

    response = client.post(
        "/v1/migrations/activities",
        json=activity_migration_payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422  # noqa: PLR2004


def test_post_activities_migrations_with_unauthenticated_user(client, unauthenticated_user):
    activity_migration_payload = {
        "month": 1714637586,
        "activities": [
            {
                "date": 1714637586,
                "user_postcode": "HD81",
                "user_age_range": "23-39",
                "rewards": [{"earned": 63, "slug": "high_five"}],
                "activity": {
                    "brisk_minutes": 109,
                    "walking_minutes": 30,
                    "steps": 1867,
                },
            }
        ],
    }

    response = client.post(
        "/v1/migrations/activities",
        json=activity_migration_payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_post_activities_migrations_with_missing_month_field(client, authenticated_user):
    activity_migration_payload = {
        "activities": [
            {
                "date": 1714637586,
                "user_postcode": "HD81",
                "user_age_range": "23-39",
                "rewards": [{"earned": 63, "slug": "high_five"}],
                "activity": {
                    "brisk_minutes": 109,
                    "walking_minutes": 30,
                    "steps": 1867,
                },
            }
        ]
    }

    response = client.post(
        "/v1/migrations/activities",
        json=activity_migration_payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422  # noqa: PLR2004


def test_get_migration_job_status_returns_started(client, authenticated_user):
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
            "/v1/migrations/activities/job-123/status",
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 200  # noqa: PLR2004
    assert response.json() == {
        "job_id": "job-123",
        "status": "started",
        "created_at": 123,
        "updated_at": 123,
    }


def test_get_migration_job_status_owner_only(client, authenticated_user):
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
            "/v1/migrations/activities/job-123/status",
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 404  # noqa: PLR2004
    assert response.json() == {"detail": "Job not found"}


def test_get_migration_job_status_not_found(client, authenticated_user):
    with patch("service.background_job_service.get_job", return_value=None):
        response = client.get(
            "/v1/migrations/activities/job-123/status",
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 404  # noqa: PLR2004
    assert response.json() == {"detail": "Job not found"}
