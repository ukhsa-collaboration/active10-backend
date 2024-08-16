from unittest.mock import patch

from service.migrations_service import load_bulk_activities_data
from tests.conftest import authenticated_user_token, user_uuid_pk, unauthenticated_user_token


def test_post_activities_migrations(client):
    with (patch("fastapi.BackgroundTasks.add_task") as mock_add_task):
        token = authenticated_user_token()
        activity_migration_payload = {
            "month": 1714637586,
            "activities": [{
                "date": 1714637586,
                "user_postcode": "HD81",
                "user_age_range": "23-39",
                "rewards": [
                    {
                        "earned": 63,
                        "slug": "high_five"
                    }
                ],
                "activity": {
                    "minsBrisk": 109,
                    "minsWalking": 30,
                    "steps": 1867
                }
            }]
        }

        response = client.post(
            "/v1/migrations/activities/",
            json=activity_migration_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        created_data = response.json()
        assert created_data == {"message": "Success"}

        mock_add_task.assert_called_once()
        args, _ = mock_add_task.call_args
        assert str(args[2].id) == str(user_uuid_pk)
        assert args[0] == load_bulk_activities_data


def test_post_activities_migrations_with_out_of_range_activities(client):
    token = authenticated_user_token()
    activity_migration_payload = {
        "month": 1714637586,
        "activities": [
            {
                "date": 1714637586,
                "user_postcode": "HD81",
                "user_age_range": "23-39",
                "rewards": [
                    {
                        "earned": 63,
                        "slug": "high_five"
                    }
                ],
                "activity": {
                    "minsBrisk": 109,
                    "minsWalking": 30,
                    "steps": 1867
                }
            },
            {
                "date": 1717229586,
                "user_postcode": "HD82",
                "user_age_range": "23-39",
                "rewards": [
                    {
                        "earned": 100,
                        "slug": "gold_star"
                    }
                ],
                "activity": {
                    "minsBrisk": 200,
                    "minsWalking": 50,
                    "steps": 3000
                }
            }
        ]
    }

    response = client.post(
        "/v1/migrations/activities/",
        json=activity_migration_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Some activities are out of the month range"}


def test_post_activities_migrations_with_empty_activities(client):
    token = authenticated_user_token()
    activity_migration_payload = {
        "month": 1714637586,
        "activities": []
    }

    response = client.post(
        "/v1/migrations/activities/",
        json=activity_migration_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_post_activities_migrations_with_unauthenticated_user(client):
    token = unauthenticated_user_token()
    activity_migration_payload = {
        "month": 1714637586,
        "activities": [{
            "date": 1714637586,
            "user_postcode": "HD81",
            "user_age_range": "23-39",
            "rewards": [
                {
                    "earned": 63,
                    "slug": "high_five"
                }
            ],
            "activity": {
                "minsBrisk": 109,
                "minsWalking": 30,
                "steps": 1867
            }
        }]
    }

    response = client.post(
        "/v1/migrations/activities/",
        json=activity_migration_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_post_activities_migrations_with_missing_month_field(client):
    token = authenticated_user_token()
    activity_migration_payload = {
        "activities": [{
            "date": 1714637586,
            "user_postcode": "HD81",
            "user_age_range": "23-39",
            "rewards": [
                {
                    "earned": 63,
                    "slug": "high_five"
                }
            ],
            "activity": {
                "minsBrisk": 109,
                "minsWalking": 30,
                "steps": 1867
            }
        }]
    }

    response = client.post(
        "/v1/migrations/activities/",
        json=activity_migration_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
