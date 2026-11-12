from http import HTTPStatus
from uuid import uuid4

from crud.motivation_crud import UserMotivationCRUD
from models.user import User
from schemas.motivation import CreateUpdateUserMotivationRequest
from tests.unittest_v3.test_users import assert_error, bearer

motivation_record_id = "test-id"


def test_create_user_motivation(client, authenticated_user):
    payload = {
        "goals": [{"text": "I want to walk more.", "id": 1}, {"text": "I want to stay healthy."}]
    }

    response = client.post("/v3/motivations/", json=payload, headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert len(data["goals"]) == 2  # noqa: PLR2004
    assert data["goals"][0] == {"text": "I want to walk more.", "id": 1}
    assert data["goals"][1] == {"text": "I want to stay healthy.", "id": None}

    global motivation_record_id  # noqa: PLW0603
    motivation_record_id = data["id"]


def test_create_user_motivation_with_missing_body(client, authenticated_user):
    response = client.post("/v3/motivations/", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_create_user_motivation_without_a_session(client, unauthenticated_user):
    payload = {"goals": [{"text": "I want to walk more.", "id": 1}]}

    response = client.post("/v3/motivations/", json=payload, headers=bearer(unauthenticated_user))

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_motivations_without_token(client):
    assert_error(client.get("/v3/motivations/"), HTTPStatus.UNAUTHORIZED, "NOT_AUTHENTICATED")


def test_get_user_motivations(client, authenticated_user):
    response = client.get("/v3/motivations/", headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data[0]["goals"][0] == {"text": "I want to walk more.", "id": 1}


def test_get_user_motivation_by_id(client, authenticated_user):
    response = client.get(
        f"/v3/motivations/{motivation_record_id}", headers=bearer(authenticated_user)
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["id"] == motivation_record_id


def test_get_unknown_motivation_is_not_found(client, authenticated_user):
    response = client.get(f"/v3/motivations/{uuid4()}", headers=bearer(authenticated_user))

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")


def test_another_users_motivation_is_not_found(client, db_session, authenticated_user):
    other_user = User(
        unique_id=str(uuid4()), nhs_number="0000000000", first_name="Other", identity_level="P9"
    )
    db_session.add(other_user)
    db_session.commit()
    payload = CreateUpdateUserMotivationRequest(goals=[{"text": "Not yours", "id": 1}])
    foreign = UserMotivationCRUD(db_session).create_motivation(other_user.id, payload)

    response = client.get(f"/v3/motivations/{foreign.id}", headers=bearer(authenticated_user))

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")


def test_get_user_motivations_without_a_session(client, unauthenticated_user):
    response = client.get("/v3/motivations/", headers=bearer(unauthenticated_user))

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_update_user_motivation(client, authenticated_user):
    payload = {
        "goals": [
            {"text": "Updated goal: Walk 10k steps daily", "id": 1},
            {"text": "Updated goal: Jog for 15 mins daily"},
        ]
    }

    response = client.put(
        f"/v3/motivations/{motivation_record_id}", json=payload, headers=bearer(authenticated_user)
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["goals"][0] == {"text": "Updated goal: Walk 10k steps daily", "id": 1}
    assert data["goals"][1] == {"text": "Updated goal: Jog for 15 mins daily", "id": None}


def test_update_user_motivation_without_a_session(client, unauthenticated_user):
    payload = {"goals": [{"text": "Unauthenticated update", "id": 1}]}

    response = client.put(
        f"/v3/motivations/{motivation_record_id}",
        json=payload,
        headers=bearer(unauthenticated_user),
    )

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_delete_user_motivation_without_a_session(client, unauthenticated_user):
    response = client.delete(
        f"/v3/motivations/{motivation_record_id}", headers=bearer(unauthenticated_user)
    )

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_delete_user_motivation(client, authenticated_user):
    response = client.delete(
        f"/v3/motivations/{motivation_record_id}", headers=bearer(authenticated_user)
    )

    assert response.status_code == HTTPStatus.NO_CONTENT


def test_deleted_motivation_is_not_found(client, authenticated_user):
    response = client.delete(
        f"/v3/motivations/{motivation_record_id}", headers=bearer(authenticated_user)
    )

    assert_error(response, HTTPStatus.NOT_FOUND, "NOT_FOUND")
