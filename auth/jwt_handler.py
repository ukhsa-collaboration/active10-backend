import time

import jwt
from fastapi import HTTPException

from utils.base_config import config, logger

JWT_SECRET = config.auth_jwt_secret
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_30_DAY_AS_SEC = 2592000


def sign_jwt(user_id: str) -> dict[str, str]:
    payload = {"user_id": user_id, "exp": time.time() + TOKEN_EXPIRY_30_DAY_AS_SEC}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token


def decode_jwt(token: str) -> dict:
    """
    Decode a JWT token.

    Args:
        token (str): The JSON Web Token (JWT) string to decode.

    Returns:
        dict: The decoded JWT payload as a dictionary.

    Raises:
        HTTPException: If the token is expired, invalid, or an error occurs during decoding.
    """
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token

    except jwt.ExpiredSignatureError as err:
        raise HTTPException(status_code=401, detail="Token is expired") from err
    except jwt.InvalidTokenError as err:
        raise HTTPException(status_code=401, detail="Token is invalid") from err
    except Exception as err:
        logger.error(f"Error while decoding token: {err!s}")
        raise HTTPException(status_code=500, detail="Something went wrong") from err
