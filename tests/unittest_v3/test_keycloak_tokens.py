import time
from http import HTTPStatus
from uuid import uuid4

from auth.v3 import auth_service
from tests.unittest_v3.conftest import create_access_token


def sync_with(client, token: str):
    return client.post("/v3/users/sync", headers={"Authorization": f"Bearer {token}"})


def test_minted_token_passes_real_validation(client, monkeypatch):
    keycloak_sub = str(uuid4())
    profile = {
        "sub": keycloak_sub,
        "idp_sub": str(uuid4()),
        "nhs_number": str(uuid4().int)[:10],
        "given_name": "Minted",
        "email": "minted@example.com",
        "birthdate": "1990-01-01",
        "identity_proofing_level": "P9",
    }
    monkeypatch.setattr(auth_service, "fetch_userinfo", lambda _token: profile)

    response = sync_with(client, create_access_token(keycloak_sub, str(uuid4())))

    assert response.status_code == HTTPStatus.OK
    assert response.json()["first_name"] == "Minted"


def test_expired_minted_token_is_rejected(client):
    token = create_access_token(str(uuid4()), str(uuid4()), exp=int(time.time()) - 60)

    response = sync_with(client, token)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_token_for_another_audience_is_rejected(client):
    token = create_access_token(str(uuid4()), str(uuid4()), aud="account")

    response = sync_with(client, token)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["error"]["code"] == "TOKEN_INVALID"
