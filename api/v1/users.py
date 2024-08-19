from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from auth.auth_bearer import get_authenticated_user_data
from models.user import User
from service.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_class=JSONResponse)
async def get_user(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    user_service: Annotated[UserService, Depends()],
):
    user_details = user_service.get_user_profile(user)
    return user_details
