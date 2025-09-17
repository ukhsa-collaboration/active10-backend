def test_create_walking_plan(client, authenticated_user):
    payload = {
        "walking_plan_data": {
            "steps_per_day": 10000,
            "walking_days": 5,
            "walking_hours": 1,
            "walking_minutes": 30,
        }
    }
    response = client.post(
        "/v1/walking_plans",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["walking_plan_data"]["steps_per_day"] == 10000


def test_create_walking_plan_with_missing_body(client, authenticated_user):
    response = client.post(
        "/v1/walking_plans",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422


def test_create_walking_plan_by_unauthenticated_user(client, unauthenticated_user):
    payload = {
        "walking_plan_data": {
            "steps_per_day": 10000,
            "walking_days": 5,
            "walking_hours": 1,
            "walking_minutes": 30,
        }
    }
    response = client.post(
        "/v1/walking_plans",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404


def test_get_user_walking_plan_by_unauthenticated_user(client, unauthenticated_user):
    response = client.get(
        "/v1/walking_plans",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404


def test_get_user_walking_plan(client, authenticated_user):
    response = client.get(
        "/v1/walking_plans",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["walking_plan_data"]["steps_per_day"] == 10000


def test_update_walking_plan(client, authenticated_user):
    payload = {
        "walking_plan_data": {
            "steps_per_day": 20000,
            "walking_days": 5,
            "walking_hours": 1,
            "walking_minutes": 30,
        }
    }
    response = client.put(
        "/v1/walking_plans",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["walking_plan_data"]["steps_per_day"] == 20000


def test_update_walking_plan_by_unauthenticated_user(client, unauthenticated_user):
    payload = {
        "walking_plan_data": {
            "steps_per_day": 20000,
            "walking_days": 5,
            "walking_hours": 1,
            "walking_minutes": 30,
        }
    }
    response = client.put(
        "/v1/walking_plans",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404


def test_delete_walking_plan_by_unauthenticated_user(client, unauthenticated_user):
    response = client.delete(
        "/v1/walking_plans",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404


def test_delete_walking_plan(client, authenticated_user):
    response = client.delete(
        "/v1/walking_plans",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 204
