from typing import Annotated

from app.api.deps import get_authenticated_user_data
from app.core.logger import logger
from app.cruds.user_crud import UserCRUD
from app.cruds.subscription_crud import SubscriptionCRUD
from app.schemas.user import (
    EmailPreferenceRequest,
    EmailPreferenceRequestPublic,
    UserResponse
)
from app.schemas.common import MessageResponse
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, status, HTTPException

router = APIRouter(prefix="/users", tags=["Users"])
router.redirect_slashes = False


@router.get(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user(
        user_data: Annotated[dict, Depends(get_authenticated_user_data)],
        user_service: Annotated[UserService, Depends()],
        user_crud: Annotated[UserCRUD, Depends()]
):
    """
    Get user details
    """
    user = user_crud.get_user_by_id(user_data.get("user_id"))

    if not user:
        logger.warning("Invalid User Access", extra={"user_id": user_data.get("user_id")})
        raise HTTPException(detail="User not found", status_code=status.HTTP_404_NOT_FOUND)

    user_details = user_service.get_user_profile(user)
    return user_details


@router.post(
    "/email_preferences/subscribe",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def subscribe_email_preference(
        user_data: Annotated[dict, Depends(get_authenticated_user_data)],
        subscription_crud: Annotated[SubscriptionCRUD, Depends()],
        payload: EmailPreferenceRequest,
):
    """
    Subscribe a user to email preferences
    """
    subscription_crud.subscribe_email_preferences(user_data.get("id"), payload.name)
    logger.info(f"User (id = {user_data.get('id')}) is subscribed to email preferences")

    return {"message": "Subscribed to email preferences"}


@router.post(
    "/email_preferences/unsubscribe",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def unsubscribe_email_preference(
        user_data: Annotated[dict, Depends(get_authenticated_user_data)],
        subscription_crud: Annotated[SubscriptionCRUD, Depends()],
        payload: EmailPreferenceRequest,
):
    """
    Unsubscribe a user from email preferences
    """
    subscription_crud.unsubscribe_email_preferences(user_data.get("id"), payload.name)
    logger.info(f"User (id = {user_data.get('id')}) is unsubscribed from email preferences")

    return {"message": "Unsubscribed from email preferences"}


@router.post(
    "/public/email_preferences/unsubscribe",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def public_unsubscribe_email_preference(
        subscription_crud: Annotated[SubscriptionCRUD, Depends()],
        payload: EmailPreferenceRequestPublic,
):
    """
    Public endpoint to unsubscribe from email preferences using the user's email.

    Args:
        Contains the user's email and the preference mailing list name.

    Returns:
        JSONResponse: Success or error message.
    """

    subscription_crud.unsubscribe_by_email(str(payload.email), payload.name)
    logger.info(
        f"User (email = {payload.email}) unsubscribed from email preferences with the name '{payload.name}'"
    )

    return {"message": "Unsubscribed successfully"}
