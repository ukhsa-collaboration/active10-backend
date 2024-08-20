from typing import Annotated

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from crud.user_crud import UserCRUD
from .jwt_handler import decode_jwt

security = HTTPBearer()

def get_authenticated_user_data(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    user_crud: Annotated[UserCRUD, Depends()],
):
    try:
        decoded_data = decode_jwt(token.credentials)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    user_data = user_crud.get_user_by_id(decoded_data.get("user_id"))

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    if not user_data.current_token or user_data.current_token != token.credentials:
        raise HTTPException(status_code=403, detail="Token is not valid")

    return user_data
