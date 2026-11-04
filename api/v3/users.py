from typing import Annotated, Any

from fastapi import APIRouter, Depends

from auth.v3.auth_service import AuthService
from auth.v3.dependencies import get_auth_token, get_current_user, get_token_claims
from crud.v3.subscription_crud import SubscriptionCRUD
from models.user import User
from schemas.user import EmailPreferenceRequest, UserResponse
from service.user_service import UserService
from utils.base_config import logger

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=UserResponse)
def get_user(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends()],
):
    return user_service.get_user_profile(current_user)


@router.post("/sync", response_model=UserResponse, status_code=200)
def sync_user(
    token: Annotated[str, Depends(get_auth_token)],
    claims: Annotated[dict[str, Any], Depends(get_token_claims)],
    auth_service: Annotated[AuthService, Depends()],
    user_service: Annotated[UserService, Depends()],
):
    """Syncs the Keycloak user into the local database and opens a backend session."""
    user = auth_service.sync_user(token, claims)
    return user_service.get_user_profile(user)


@router.post("/email_preferences/subscribe")
def subscribe_email_preference(
    current_user: Annotated[User, Depends(get_current_user)],
    subscription_crud: Annotated[SubscriptionCRUD, Depends()],
    payload: EmailPreferenceRequest,
):
    subscription_crud.subscribe_email_preferences(current_user.id, payload.name)
    logger.info(f"User (id = {current_user.id}) is subscribed to email preferences")
    return {"message": "Subscribed to email preferences"}


@router.post("/email_preferences/unsubscribe")
def unsubscribe_email_preference(
    current_user: Annotated[User, Depends(get_current_user)],
    subscription_crud: Annotated[SubscriptionCRUD, Depends()],
    payload: EmailPreferenceRequest,
):
    subscription_crud.unsubscribe_email_preferences(current_user.id, payload.name)
    logger.info(f"User (id = {current_user.id}) is unsubscribed from email preferences")
    return {"message": "Unsubscribed from email preferences"}
