from unittest.mock import patch

import pytest

from tests.unittest.conftest import override_get_db_context_session


def test_post_activities_migrations(client, authenticated_user, db_session):
    with (
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

        assert response.status_code == 201  # noqa: PLR2004
        created_data = response.json()
        assert created_data == {"message": "Success"}


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


def test_post_activities_migrations_with_effort_and_feeling(client, authenticated_user):
    activity_migration_payload = {
        "month": 1714637586,
        "activities": [
            {
                "date": 1714637586,
                "user_postcode": "HD81",
                "user_age_range": "23-39",
                "activity": {
                    "brisk_minutes": 20,
                    "walking_minutes": 30,
                    "steps": 0,
                    "effort": 10,
                    "feeling": 1,
                },
            },
            {
                "date": 1714637586,
                "user_postcode": "HD81",
                "user_age_range": "23-39",
                "activity": {
                    "brisk_minutes": 109,
                    "walking_minutes": 30,
                    "steps": 1867,
                    "feeling": 2,
                },
            },
        ],
    }

    with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        response = client.post(
            "/v1/migrations/activities",
            json=activity_migration_payload,
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

    assert response.status_code == 201  # noqa: PLR2004
    args, _kwargs = mock_add_task.call_args
    published = [a["activity"] for a in args[1].model_dump()["activities"]]
    assert (published[0]["effort"], published[0]["feeling"]) == (10, 1)
    assert (published[1]["effort"], published[1]["feeling"]) == (None, None)


@pytest.mark.parametrize("scores", [{"effort": 0}, {"effort": 11}, {"feeling": 3}])
def test_post_activities_migrations_with_out_of_range_effort_or_feeling(
    client, authenticated_user, scores
):
    activity_migration_payload = {
        "month": 1714637586,
        "activities": [
            {
                "date": 1714637586,
                "user_postcode": "HD81",
                "user_age_range": "23-39",
                "activity": {"brisk_minutes": 20, "walking_minutes": 30, "steps": 0, **scores},
            }
        ],
    }

    response = client.post(
        "/v1/migrations/activities",
        json=activity_migration_payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422  # noqa: PLR2004
