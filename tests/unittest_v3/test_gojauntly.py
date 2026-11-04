from http import HTTPStatus

import pytest
from fastapi import HTTPException

from api.v3 import gojauntly
from tests.unittest_v3.test_users import assert_error, bearer

SEARCH = {"page": 1, "amount": 5, "postcode": "LS1 1AA"}
ENDPOINTS = [
    ("curated_walk_search", "/v3/curated-walks/search", SEARCH),
    ("curated_walk_retrieve", "/v3/curated-walks/walk-1", {"includeSteps": True}),
    ("dynamic_routes_circular_collection", "/v3/routing/circular/collection", {"max_paths": 1}),
]


def recording(result):
    def call(**kwargs):
        call.kwargs = kwargs
        return result

    return call


def failing(status_code: int):
    def call(**_kwargs):
        raise HTTPException(status_code=status_code, detail={"errors": [{"detail": "upstream"}]})

    return call


@pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
def test_gojauntly_result_is_returned(client, authenticated_user, monkeypatch, method, path, body):  # noqa: PLR0913
    fake = recording({"data": [{"id": "walk-1"}]})
    monkeypatch.setattr(gojauntly.client, method, fake)

    response = client.post(path, json=body, headers=bearer(authenticated_user))

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"data": [{"id": "walk-1"}]}
    assert set(body) <= set(fake.kwargs["data"])


def test_curated_walk_retrieve_passes_the_walk_id(client, authenticated_user, monkeypatch):
    fake = recording({})
    monkeypatch.setattr(gojauntly.client, "curated_walk_retrieve", fake)

    client.post("/v3/curated-walks/walk-42", json={}, headers=bearer(authenticated_user))

    assert fake.kwargs["id"] == "walk-42"


@pytest.mark.parametrize(
    ("upstream_status", "status_code", "code"),
    [
        (400, HTTPStatus.BAD_REQUEST, "INVALID_REQUEST"),
        (422, HTTPStatus.BAD_REQUEST, "INVALID_REQUEST"),
        (401, HTTPStatus.BAD_GATEWAY, "UPSTREAM_ERROR"),
        (404, HTTPStatus.BAD_GATEWAY, "UPSTREAM_ERROR"),
        (500, HTTPStatus.BAD_GATEWAY, "UPSTREAM_ERROR"),
    ],
)
def test_gojauntly_failures_are_coded(  # noqa: PLR0913
    client, authenticated_user, monkeypatch, upstream_status, status_code, code
):
    monkeypatch.setattr(gojauntly.client, "curated_walk_search", failing(upstream_status))

    response = client.post(
        "/v3/curated-walks/search", json=SEARCH, headers=bearer(authenticated_user)
    )

    assert_error(response, status_code, code)
    assert "www-authenticate" not in response.headers


def test_gojauntly_without_a_session(client, unauthenticated_user, monkeypatch):
    monkeypatch.setattr(gojauntly.client, "curated_walk_search", recording({}))

    response = client.post(
        "/v3/curated-walks/search", json=SEARCH, headers=bearer(unauthenticated_user)
    )

    assert_error(response, HTTPStatus.UNAUTHORIZED, "SESSION_NOT_FOUND")


def test_gojauntly_without_token(client):
    response = client.post("/v3/curated-walks/search", json=SEARCH)

    assert_error(response, HTTPStatus.UNAUTHORIZED, "NOT_AUTHENTICATED")
