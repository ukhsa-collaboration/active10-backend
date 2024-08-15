from uuid import uuid4

from tests.conftest import authenticated_user_token, unauthenticated_user_token

target_id = None
invalid_target_id = uuid4()


def test_create_daily_target(client):
    token = authenticated_user_token()
    payload = {
        "daily_target": 20,
        "date": 12341234
    }
    response = client.post(
        "/v1/daily_targets/",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    data = response.json()
    global target_id
    target_id = data["id"]
    assert data["daily_target"] == 20


def test_create_daily_target_with_missing_body(client):
    token = authenticated_user_token()
    response = client.post(
        "/v1/daily_targets/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 422


def test_create_daily_target_by_unauthenticated_user(client):
    token = unauthenticated_user_token()
    payload = {
        "daily_target": 20,
        "date": 12341234
    }
    response = client.post(
        "/v1/daily_targets/",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


def test_get_user_all_daily_targets_by_unauthenticated_user(client):
    token = unauthenticated_user_token()
    response = client.get(
        "/v1/daily_targets/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


def test_get_user_all_daily_target(client):
    token = authenticated_user_token()
    response = client.get(
        "/v1/daily_targets/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


def test_get_user_single_daily_target(client):
    token = authenticated_user_token()
    global target_id

    response = client.get(
        f"/v1/daily_targets/{target_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == target_id


def test_get_user_single_invalid_daily_target(client):
    token = authenticated_user_token()
    global invalid_target_id

    response = client.get(
        f"/v1/daily_targets/{invalid_target_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


def test_update_daily_target(client):
    token = authenticated_user_token()
    global target_id
    payload = {
        "date": 123499,
        "daily_target": 10
    }
    response = client.put(
        f"/v1/daily_targets/{target_id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["daily_target"] == 10


def test_update_daily_target_by_unauthenticated_user(client):
    token = unauthenticated_user_token()
    global target_id

    payload = {
        "daily_target": 20,
        "date": 12341234
    }

    response = client.put(
        f"/v1/daily_targets/{target_id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


def test_delete_daily_target_by_unauthenticated_user(client):
    token = unauthenticated_user_token()
    global target_id

    response = client.delete(
        f"/v1/daily_targets/{target_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


def test_delete_daily_target(client):
    token = authenticated_user_token()
    global target_id

    response = client.delete(
        f"/v1/daily_targets/{target_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 204


def test_delete_invalid_daily_target(client):
    token = authenticated_user_token()
    global invalid_target_id

    response = client.delete(
        f"/v1/daily_targets/{invalid_target_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
