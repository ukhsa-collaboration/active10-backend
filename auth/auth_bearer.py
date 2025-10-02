from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from crud.user_crud import UserCRUD
from service.redis_service import RedisService, get_redis_service
from utils.base_config import logger

from .jwt_handler import decode_jwt

security = HTTPBearer()


def get_authenticated_user_data(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    user_crud: Annotated[UserCRUD, Depends()],
    redis_service: RedisService = Depends(get_redis_service),  # noqa: B008
) -> dict[str, Any]:
    """
    Validate a JWT-based user token against cache and database.

    Args:
        token: Authorization token extracted from request.
        user_crud: Data access object for user retrieval.
        redis_service: Service for caching token validation results.

    Returns:
        A dict containing authenticated user information.

    Raises:
        HTTPException: If the token is invalid, expired, or the user is not found.
    """
    token_hash = redis_service.hash_token(token.credentials)
    cached_auth_data = redis_service.get_auth_cache(token_hash)

    if cached_auth_data:
        logger.info(f"Cache hit for auth - user_id: {cached_auth_data['user_id']}")
        if not cached_auth_data["valid"]:
            raise HTTPException(status_code=403, detail="Token is not valid")

        return cached_auth_data

    decoded_data = decode_jwt(token.credentials)
    user_id = decoded_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Token is not valid")

    # User data not in cache, fetch from database
    user = user_crud.get_user_by_id(user_id)

    if user:
        user_token = user.token

        if user_token:
            user_token_hash = redis_service.hash_token(user_token.token)
            expires_in = decoded_data.get("exp")
            cache_ttl = max(0, int(expires_in - datetime.now(timezone.utc).timestamp()))  # noqa: UP017 Not supported in Python 3.10

            # Ensure token match
            if token_hash != user_token_hash:
                logger.warning(f"Token mismatch for user_id={user_id}")
                _ = redis_service.set_auth_cache(token_hash, user_id, cache_ttl, valid=False)
                raise HTTPException(status_code=403, detail="Token is not valid")

            # Cache valid token
            auth_cached = redis_service.set_auth_cache(user_token_hash, user_id, cache_ttl)

            if auth_cached:
                logger.debug(f"Auth cache set for user: {user_id}")
            else:
                logger.debug(f"Auth cache unable to set for user: {user_id}")

            return {"user_id": user_id, "valid": True}

        else:
            raise HTTPException(status_code=403, detail="Token is not valid")

    else:
        raise HTTPException(status_code=404, detail="User not found")
