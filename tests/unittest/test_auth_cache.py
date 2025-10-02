from http import HTTPStatus

from fastapi.testclient import TestClient

from models import User
from service.redis_service import RedisService


def test_auth_cache_set_and_hit(client: TestClient, authenticated_user: User, db_session) -> None:
    redis_client = RedisService.get_client()

    # Ensure cache is empty at start
    token = authenticated_user.token.token
    token_hash = RedisService.hash_token(token)
    if redis_client:
        redis_client.delete(token_hash)

    # Act: first request should be a cache miss and then set cache
    resp1 = client.get(
        "/v1/users/", headers={"Authorization": f"Bearer {authenticated_user.token.token}"}
    )
    assert resp1.status_code == HTTPStatus.OK

    # Assert: cache should be set
    cached = RedisService.get_auth_cache(token_hash)
    assert cached is not None
    assert cached.get("user_id") == str(authenticated_user.id)

    # Act: second request should hit cache and still succeed
    resp2 = client.get("/v1/users/", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == HTTPStatus.OK


def test_auth_cache_invalidation_on_logout(
    client: TestClient, authenticated_user: User, db_session
) -> None:
    token = authenticated_user.token.token
    token_hash = RedisService.hash_token(token)
    redis_client = RedisService.get_client()
    if redis_client:
        redis_client.delete(token_hash)

    resp = client.get("/v1/users/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == HTTPStatus.OK

    # Act: call logout
    resp = client.post("/nhs_login/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == HTTPStatus.OK

    assert RedisService.get_auth_cache(token_hash) is None
