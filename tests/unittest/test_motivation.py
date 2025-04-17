motivation_record_id = "test-id"


def test_create_user_motivation(client, authenticated_user):
    payload = {
        "goals": [
            {"text": "I want to walk more."},
            {"text": "I want to stay healthy."}
        ]
    }

    response = client.post(
        "/v1/motivations/",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["goals"]) == 2
    assert data["goals"][0]["text"] == "I want to walk more."

    global motivation_record_id
    motivation_record_id = data["id"]


def test_create_user_motivation_with_missing_body(client, authenticated_user):
    response = client.post(
        "/v1/motivations/",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422


def test_create_user_motivation_unauthenticated(client, unauthenticated_user):
    payload = {
        "goals": [
            {"text": "I want to walk more."}
        ]
    }

    response = client.post(
        "/v1/motivations/",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404


def test_get_user_motivation(client, authenticated_user):
    response = client.get(
        "/v1/motivations/",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert type(data) == list
    assert data[0]["goals"][0]["text"] == "I want to walk more."


def test_get_user_motivation_unauthenticated(client, unauthenticated_user):
    response = client.get(
        "/v1/motivations/",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404


def test_update_user_motivation(client, authenticated_user):
    payload = {
        "goals": [
            {"text": "Updated goal: Walk 10k steps daily"}
        ]
    }

    response = client.put(
        f"/v1/motivations/{motivation_record_id}",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["goals"][0]["text"] == "Updated goal: Walk 10k steps daily"


def test_update_user_motivation_unauthenticated(client, unauthenticated_user):
    payload = {
        "goals": [
            {"text": "Unauthenticated update"}
        ]
    }

    response = client.put(
        f"/v1/motivations/{motivation_record_id}",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404


def test_delete_user_motivation(client, authenticated_user):
    response = client.delete(
        f"/v1/motivations/{motivation_record_id}",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 204


def test_delete_user_motivation_unauthenticated(client, unauthenticated_user):
    response = client.delete(
        f"/v1/motivations/{motivation_record_id}",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404
