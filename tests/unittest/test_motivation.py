motivation_record_id = "test-id"


def test_create_user_motivation(client, authenticated_user):
    payload = {
        "goals": [{"text": "I want to walk more.", "id": 1}, {"text": "I want to stay healthy."}]
    }

    response = client.post(
        "/v1/motivations/",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 201  # noqa: PLR2004
    data = response.json()
    assert len(data["goals"]) == 2  # noqa: PLR2004
    assert data["goals"][0]["text"] == "I want to walk more."
    assert data["goals"][0]["id"] == 1
    assert data["goals"][1]["text"] == "I want to stay healthy."
    assert data["goals"][1]["id"] is None

    global motivation_record_id  # noqa: PLW0603
    motivation_record_id = data["id"]


def test_create_user_motivation_with_missing_body(client, authenticated_user):
    response = client.post(
        "/v1/motivations/",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 422  # noqa: PLR2004


def test_create_user_motivation_unauthenticated(client, unauthenticated_user):
    payload = {"goals": [{"text": "I want to walk more.", "id": 1}]}

    response = client.post(
        "/v1/motivations/",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_get_user_motivation(client, authenticated_user):
    response = client.get(
        "/v1/motivations/",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert type(data) == list  # noqa: E721
    assert data[0]["goals"][0]["text"] == "I want to walk more."
    assert data[0]["goals"][0]["id"] == 1
    assert data[0]["goals"][1]["text"] == "I want to stay healthy."
    assert data[0]["goals"][1]["id"] is None


def test_get_user_motivation_unauthenticated(client, unauthenticated_user):
    response = client.get(
        "/v1/motivations/",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_update_user_motivation(client, authenticated_user):
    payload = {
        "goals": [
            {"text": "Updated goal: Walk 10k steps daily", "id": 1},
            {"text": "Updated goal: Jog for 15 mins daily"},
        ]
    }

    response = client.put(
        f"/v1/motivations/{motivation_record_id}",
        json=payload,
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 200  # noqa: PLR2004
    data = response.json()
    assert data["goals"][0]["text"] == "Updated goal: Walk 10k steps daily"
    assert data["goals"][0]["id"] == 1
    assert data["goals"][1]["text"] == "Updated goal: Jog for 15 mins daily"
    assert data["goals"][1]["id"] is None


def test_update_user_motivation_unauthenticated(client, unauthenticated_user):
    payload = {"goals": [{"text": "Unauthenticated update", "id": 1}]}

    response = client.put(
        f"/v1/motivations/{motivation_record_id}",
        json=payload,
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004


def test_delete_user_motivation(client, authenticated_user):
    response = client.delete(
        f"/v1/motivations/{motivation_record_id}",
        headers={"Authorization": f"Bearer {authenticated_user.token.token}"},
    )

    assert response.status_code == 204  # noqa: PLR2004


def test_delete_user_motivation_unauthenticated(client, unauthenticated_user):
    response = client.delete(
        f"/v1/motivations/{motivation_record_id}",
        headers={"Authorization": f"Bearer {unauthenticated_user.token.token}"},
    )

    assert response.status_code == 404  # noqa: PLR2004
