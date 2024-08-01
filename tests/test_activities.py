from datetime import datetime

from tests.conftest import authenticated_user_token


def test_create_activities(client):
    token = authenticated_user_token()
    response = client.post(
        "/v1/activities/",
        json={
            "user_id": 99999999,
            "mins_brisk": 30,
            "mins_walking": 30,
            "steps": 5000,
            "date": int(datetime.timestamp(datetime.now())),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    created_data = response.json()
    assert created_data["mins_brisk"] == 30
    assert created_data["mins_walking"] == 30
    assert created_data["steps"] == 5000


def test_create_activities_missing_fields(client):
    token = authenticated_user_token()
    response = client.post(
        "/v1/activities/",
        json={
            "mins_brisk": 30,
            "mins_walking": 30,
            "steps": 5000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_create_activities_invalid_data_types(client):
    token = authenticated_user_token()
    response = client.post(
        "/v1/activities/",
        json={
            "mins_brisk": "thirty",  # Invalid type
            "mins_walking": 30,
            "steps": 5000,
            "date": "2021-01-01"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 422
