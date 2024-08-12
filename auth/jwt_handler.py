import time
from typing import Dict

import jwt

from utils.base_config import config

JWT_SECRET = config.secret
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_30_DAY_AS_SEC = 2592000


def sign_jwt(user_id: str) -> Dict[str, str]:
    payload = {"user_id": user_id, "expires": time.time() + TOKEN_EXPIRY_30_DAY_AS_SEC}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token


def decode_jwt(token: str) -> dict:
    # An exception will be raised by PyJWT module if it can't be decoded
    decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

    return decoded_token

