from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from auth.auth_bearer import get_authenticated_user_data
from crud.subscription_crud import SubscriptionCRUD
from models.user import User
from schemas.user import EmailPreferenceRequest
from service.user_service import UserService
from utils.base_config import logger

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_class=JSONResponse)
async def get_user(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    user_service: Annotated[UserService, Depends()],
):
    user_details = user_service.get_user_profile(user)
    return user_details


@router.post("/email_preferences/subscribe/", response_class=JSONResponse)
async def subscribe_email_preference(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    subscription_crud: Annotated[SubscriptionCRUD, Depends()],
    payload: EmailPreferenceRequest,
):
    subscription_crud.subscribe_email_preferences(user.id, payload.name)
    logger.info(f"User (id = {user.id}) is subscribed to email preferences")

    return JSONResponse(status_code=200, content={"message": "Subscribed to email preferences"})


@router.post("/email_preferences/unsubscribe/", response_class=JSONResponse)
async def unsubscribe_email_preference(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    subscription_crud: Annotated[SubscriptionCRUD, Depends()],
    payload: EmailPreferenceRequest,
):
    subscription_crud.unsubscribe_email_preferences(user.id, payload.name)
    logger.info(f"User (id = {user.id}) is unsubscribed from email preferences")

    return JSONResponse(status_code=200, content={"message": "Unsubscribed from email preferences"})