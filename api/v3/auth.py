from typing import Annotated, Any

from fastapi import APIRouter, Depends

from auth.v3.auth_service import AuthService
from auth.v3.dependencies import get_current_user, get_token_claims
from models.user import User
from schemas.auth import RefreshTokenRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/logout", status_code=200)
def logout(
    payload: RefreshTokenRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    claims: Annotated[dict[str, Any], Depends(get_token_claims)],
    auth_service: Annotated[AuthService, Depends()],
):
    """Revokes the refresh token at Keycloak and closes this session."""
    auth_service.logout(current_user, claims["sid"], payload.refresh_token)
    return {"message": "User logged out successfully"}


@router.post("/disconnect", status_code=200)
def disconnect(
    payload: RefreshTokenRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    claims: Annotated[dict[str, Any], Depends(get_token_claims)],
    auth_service: Annotated[AuthService, Depends()],
):
    """Revokes the refresh token at Keycloak and deletes the user's account and data."""
    auth_service.disconnect(current_user, claims["sid"], payload.refresh_token)
    return {"message": "User disconnected successfully"}
