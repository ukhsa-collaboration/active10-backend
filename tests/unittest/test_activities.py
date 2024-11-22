from datetime import datetime
from unittest.mock import patch

from service.activity_service import load_activity_data
from tests.unittest.conftest import user_uuid_pk, override_get_db_context_session


def test_create_activities(client, authenticated_user, db_session):
    with (
        patch("fastapi.BackgroundTasks.add_task") as mock_add_task,
        patch(
            "crud.activities_crud.get_db_context_session",
            lambda: override_get_db_context_session(db_session),
        ),
    ):
        activity_payload = {
            "date": 1714637586,
            "user_postcode": "HD81",
            "user_age_range": "23-39",
            "rewards": [{"earned": 63, "slug": "high_five"}],
            "activity": {"brisk_minutes": 109, "walking_minutes": 30, "steps": 1867},
        }

        response = client.post(
            "/v1/activities/",
            json=activity_payload,
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

        assert response.status_code == 201
        created_data = response.json()
        assert created_data["date"] == 1714637586
        assert created_data["user_postcode"] == "HD81"

        mock_add_task.assert_called_once()
        args, kwargs = mock_add_task.call_args
        assert str(args[2]) == str(user_uuid_pk)
        assert args[0] == load_activity_data


def test_create_activities_without_rewards(client, authenticated_user, db_session):
    with (
        patch("fastapi.BackgroundTasks.add_task") as mock_add_task,
        patch(
            "crud.activities_crud.get_db_context_session",
            lambda: override_get_db_context_session(db_session),
        ),
    ):
        activity_payload = {
            "date": 1714637586,
            "user_postcode": "HD81",
            "user_age_range": "23-39",
            "activity": {"brisk_minutes": 109, "walking_minutes": 30, "steps": 1867},
        }

        response = client.post(
            "/v1/activities/",
            json=activity_payload,
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

        assert response.status_code == 201
        created_data = response.json()
        assert created_data["date"] == 1714637586
        assert created_data["user_postcode"] == "HD81"

        mock_add_task.assert_called_once()
        args, kwargs = mock_add_task.call_args
        assert str(args[2]) == str(user_uuid_pk)
        assert args[0] == load_activity_data


def test_create_activities_missing_fields(client, authenticated_user):
    activity_payload = {
        "user_postcode": "HD81",
        "user_age_range": "23-39",
        "rewards": [{"earned": 63, "slug": "high_five"}],
        "activity": {"brisk_minutes": 109, "steps": 1867},
    }

    response = client.post(
        "/v1/activities/",
        json=activity_payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422


def test_create_activities_invalid_data_types(client, authenticated_user):
    activity_payload = {
        "date": datetime.now().isoformat(),
        "user_postcode": "HD81",
        "user_age_range": "23-39",
        "rewards": [{"earned": 63, "slug": "high_five"}],
        "activity": {"brisk_minutes": "ten", "walking_minutes": 30, "steps": 1867},
    }

    response = client.post(
        "/v1/activities/",
        json=activity_payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422


def test_list_activities(client, authenticated_user, db_session):
    with patch(
        "crud.activities_crud.get_db_context_session",
        lambda: override_get_db_context_session(db_session),
    ):
        response = client.get(
            "/v1/activities/",
            headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
        )

        assert response.status_code == 200
        response_data = response.json()
        assert "id" in response_data[0]
        assert response.status_code == 200
        response_data = response.json()
        assert "id" in response_data[0]


def test_list_activities_by_unauthenticated_user(client, unauthenticated_user):
    response = client.get(
        "/v1/activities/",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404
