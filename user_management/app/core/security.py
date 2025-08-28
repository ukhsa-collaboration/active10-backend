import time
from typing import Dict

import jwt
from app.core.config import settings

JWT_SECRET = settings.AUTH_JWT_SECRET
JWT_ALGORITHM = settings.JWT_ALGORITHM
AUTH_JWT_EXPIRY_IN_SECONDS = settings.AUTH_JWT_EXPIRY_IN_SECONDS


def sign_jwt(user_id: str) -> Dict[str, str]:
    payload = {"user_id": user_id, "exp": time.time() + AUTH_JWT_EXPIRY_IN_SECONDS}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token
