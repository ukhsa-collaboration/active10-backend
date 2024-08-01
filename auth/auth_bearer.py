from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .jwt_handler import decode_jwt


class JWTBearer(HTTPBearer):
    def __init__(self) -> None:
        self.user_id: str | None = None
        super().__init__()

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        try:
            decoded = decode_jwt(credentials.credentials)
            self.user_id = decoded["user_id"]
            return self.user_id

        except Exception as err:
            raise HTTPException(status_code=403, detail=str(err))


authenticated_user_id = JWTBearer()
