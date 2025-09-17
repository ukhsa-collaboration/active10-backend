from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from crud.token_crud import TokenCRUD
from crud.user_crud import UserCRUD
from service.redis_service import RedisService, get_redis_service
from utils.base_config import logger

from .jwt_handler import decode_jwt

security = HTTPBearer()


def get_authenticated_user_data(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    user_crud: Annotated[UserCRUD, Depends()],
    token_crud: Annotated[TokenCRUD, Depends()],
    redis_service: RedisService = Depends(get_redis_service),  # noqa: B008
) -> dict[str, str]:
    try:
        decoded_data = decode_jwt(token.credentials)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))  # noqa: B904 - will likely need to be changed to avoid returning raw exceptions to clients

    user_id = decoded_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Invalid token payload")

    # Create token hash for caching
    token_hash = redis_service.hash_token(token.credentials)

    # Check if token validation is cached
    cached_user_id = redis_service.get_token_cache(token_hash, user_id)

    if cached_user_id:
        user_data = redis_service.get_user_cache(user_id)
        if user_data:
            logger.debug(f"Cache hit for user {user_id}")
            return user_data
        else:
            # User data not in cache, fetch from database
            user = user_crud.get_user_by_id(user_id)
            if user:
                # Create minimal user data dict for caching
                user_data = {"user_id": str(user.id), "email": user.email or ""}
                redis_service.set_user_cache(user_id, user_data)
                logger.debug(f"Cached user data for {user_id}")
                return user_data
            else:
                # User not found, invalidate token cache
                redis_service.delete_token_cache(token_hash, user_id)
                raise HTTPException(status_code=404, detail="User not found")
    else:
        # Token not in cache or invalid, validate against database
        user = user_crud.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Validate token against database
        if not token_crud.validate_user_token(user.id, token.credentials):
            raise HTTPException(status_code=403, detail="Token is not valid")

        # Create minimal user data dict
        user_data = {"user_id": str(user.id), "email": user.email or ""}

        # Cache both token validation and user data
        redis_service.set_token_cache(token_hash, user_id)
        redis_service.set_user_cache(user_id, user_data)
        logger.debug(f"Cached token and user data for {user_id}")

        return user_data
