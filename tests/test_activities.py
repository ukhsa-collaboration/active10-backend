from datetime import datetime
from unittest.mock import patch

from service.activity_service import load_activity_data
from tests.conftest import authenticated_user_token, user_uuid_pk


def test_create_activities(client):
    with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        token = authenticated_user_token()
        activity_payload = {
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
        }

        response = client.post(
            "/v1/activities/",
            json=activity_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        created_data = response.json()
        assert created_data == {"message": "Success"}

        mock_add_task.assert_called_once()
        args, kwargs = mock_add_task.call_args
        assert str(args[2].id) == str(user_uuid_pk)
        assert args[0] == load_activity_data


def test_create_activities_without_rewards(client):
    with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        token = authenticated_user_token()
        activity_payload = {
            "date": 1714637586,
            "user_postcode": "HD81",
            "user_age_range": "23-39",
            "activity": {
                "minsBrisk": 109,
                "minsWalking": 30,
                "steps": 1867
            }
        }

        response = client.post(
            "/v1/activities/",
            json=activity_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        created_data = response.json()
        assert created_data == {"message": "Success"}

        mock_add_task.assert_called_once()
        args, kwargs = mock_add_task.call_args
        assert str(args[2].id) == str(user_uuid_pk)
        assert args[0] == load_activity_data


def test_create_activities_missing_fields(client):
    token = authenticated_user_token()

    activity_payload = {
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
            "steps": 1867
        }
    }

    response = client.post(
        "/v1/activities/",
        json=activity_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_create_activities_invalid_data_types(client):
    token = authenticated_user_token()

    activity_payload = {
        "date": datetime.now().isoformat(),
        "user_postcode": "HD81",
        "user_age_range": "23-39",
        "rewards": [
            {
                "earned": 63,
                "slug": "high_five"
            }
        ],
        "activity": {
            "minsBrisk": "ten",
            "minsWalking": 30,
            "steps": 1867
        }
    }

    response = client.post(
        "/v1/activities/",
        json=activity_payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 422
