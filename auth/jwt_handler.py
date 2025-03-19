import time
from typing import Dict

import jwt

from utils.base_config import config

JWT_SECRET = config.auth_jwt_secret
JWT_ALGORITHM = "HS256"
JWT_TOKEN_EXPIRY_IN_SECONDS = config.auth_jwt_expiry_in_seconds


def sign_jwt(user_id: str) -> Dict[str, str]:
    payload = {"user_id": user_id, "exp": time.time() + JWT_TOKEN_EXPIRY_IN_SECONDS}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token


def decode_jwt(token: str) -> dict:
    # An exception will be raised by PyJWT module if it can't be decoded
    decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

    return decoded_token
