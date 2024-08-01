from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse
from models.user import User
from service.auth_service import get_authenticated_user_data


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_class=JSONResponse)
async def get_user(user: Annotated[User, Depends(get_authenticated_user_data)]):
    return user


@router.post("/switch_device")
async def switch_device():
    pass


@router.put("/disconnect_nhs")
async def disconnect_nhs():
    pass
