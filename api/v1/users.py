from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from starlette.responses import JSONResponse

from crud.subscription_crud import SubscriptionCRUD
from crud.user_crud import UserCRUD
from models.user import User
from schemas.user import EmailPreferenceRequest
from service.user_service import UserService
from utils.base_config import logger

router = APIRouter(prefix="/users", tags=["users"])
router.redirect_slashes = False  # avoid 307 redirects - they're problematic behind API Gateway

# Kept in this file just for demo purposes
def get_authenticated_user_data(
    user_id: Annotated[str | None, Header(alias="Bh-User-Id")] = None,
    user_crud: Annotated["UserCRUD", Depends()] = Depends(),
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing Bh-User-Id header")
    user = user_crud.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# We could use two decorators here to allow "/" but a URL ending in / isn't supported by API Gateway
# so it would be additional verbosity without any benefit.
@router.get("")
async def get_user(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    user_service: Annotated[UserService, Depends()],
):
    user_details = user_service.get_user_profile(user)
    return user_details


@router.post("/email_preferences/subscribe")
async def subscribe_email_preference(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    subscription_crud: Annotated[SubscriptionCRUD, Depends()],
    payload: EmailPreferenceRequest,
):
    subscription_crud.subscribe_email_preferences(user.id, payload.name)
    logger.info(f"User (id = {user.id}) is subscribed to email preferences")

    return JSONResponse(status_code=200, content={"message": "Subscribed to email preferences"})


@router.post("/email_preferences/unsubscribe")
async def unsubscribe_email_preference(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    subscription_crud: Annotated[SubscriptionCRUD, Depends()],
    payload: EmailPreferenceRequest,
):
    subscription_crud.unsubscribe_email_preferences(user.id, payload.name)
    logger.info(f"User (id = {user.id}) is unsubscribed from email preferences")

    return JSONResponse(status_code=200, content={"message": "Unsubscribed from email preferences"})