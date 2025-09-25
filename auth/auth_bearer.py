from datetime import datetime, timezone
from typing import Annotated

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
) -> dict[str, str]:
    token_hash = redis_service.hash_token(token.credentials)
    cached_auth_data = redis_service.get_auth_cache(token_hash)

    if cached_auth_data:
        logger.info(f"Cache hit for auth - user_id: {cached_auth_data['user_id']}")
        return cached_auth_data

    decoded_data = decode_jwt(token.credentials)

    user_id = decoded_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Invalid token payload")

    # User data not in cache, fetch from database
    user = user_crud.get_user_by_id(user_id)

    if user:
        user_token = user.token

        if user_token:
            user_token_hash = redis_service.hash_token(user_token.token)
            request_token_hash = redis_service.hash_token(token.credentials)

            if request_token_hash != user_token_hash:
                logger.warning("Token mismatch")
                raise HTTPException(status_code=403, detail="Token is not valid")

            decoded_data = decode_jwt(user_token.token)
            expires_in = decoded_data.get("exp")
            cache_ttl = int(expires_in - datetime.now(timezone.utc).timestamp())  # noqa: UP017 Not supported in Python 3.10
            auth_cached = redis_service.set_auth_cache(user_token_hash, user_id, cache_ttl)

            if auth_cached:
                logger.debug(f"Auth cache set for user: {user_id}")
            else:
                logger.debug(f"Auth cache ünable to set for user: {user_id}")

            return {"user_id": user_id}

        else:
            raise HTTPException(status_code=403, detail="Token is not valid")

    else:
        raise HTTPException(status_code=404, detail="User not found")
