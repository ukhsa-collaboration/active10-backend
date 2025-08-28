from datetime import datetime, timezone
from typing import Annotated

from app.core.logger import logger
from app.db.session import get_db_session
from app.models import UserStatus, UserDeleteReason, DeleteAudit
from app.schemas.common import MessageResponse
from app.cruds.user_crud import UserCRUD
from app.services.nhs_login_service import NHSLoginService
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .deps import get_authenticated_user_data

router = APIRouter(prefix="/nhs_login", tags=["NHS Login"])
router.redirect_slashes = False


@router.get("/{app_name}/{app_internal_id}")
async def nhs_login(
        app_name: str, app_internal_id: str, service: NHSLoginService = Depends()
):
    """
    Generate a URL for NHS OIDC based login with app name and app internal ID.
    """
    url = service.get_nhs_login_url(app_name, app_internal_id)
    return RedirectResponse(url)


@router.get(
    "/callback",
    response_class=RedirectResponse,
    status_code=status.HTTP_301_MOVED_PERMANENTLY,
)
async def nhs_login_callback(request: Request, service: NHSLoginService = Depends()):
    """
    Process callback from NHS Login Service.It stores the user information
    and return system generated token in redirect response.
    """
    req_args = dict(request.query_params)
    deep_link = service.process_callback(req_args)
    return RedirectResponse(deep_link)


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(
        user_data: Annotated[dict, Depends(get_authenticated_user_data)],
        user_crud: Annotated[UserCRUD, Depends()],
        db: Session = Depends(get_db_session),
):
    """
    Logout the user and revoke access of user token.
    """
    user = user_crud.get_user_by_id(user_data.get("user_id"))

    if not user:
        logger.warning("Invalid User Access", extra={"user_id": user_data.get("user_id")})
        raise HTTPException(detail="User not found", status_code=status.HTTP_404_NOT_FOUND)

    user.status = UserStatus.LOGOUT.value
    user.status_updated_at = datetime.now(timezone.utc)
    user_token = user.token
    db.delete(user_token)
    db.commit()

    return {"message": "User logged out successfully"}


@router.post(
    "/disconnect", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def disconnect(
        user_data: Annotated[dict, Depends(get_authenticated_user_data)],
        user_crud: Annotated[UserCRUD, Depends(UserCRUD)],
        db: Session = Depends(get_db_session),
):
    """
    Logout and delete user record.
    """
    try:
        user = user_crud.get_user_by_id(user_data.get("user_id"))

        if not user:
            logger.warning("Invalid User Access", extra={"user_id": user_data.get("user_id")})
            raise HTTPException(detail="User not found", status_code=status.HTTP_404_NOT_FOUND)

        db.delete(user)

        delete_audit = DeleteAudit(
            user_id=user.id, delete_reason=UserDeleteReason.DISCONNECTED.value
        )
        db.add(delete_audit)
        db.commit()

        return {"message": "User disconnected successfully"}

    except HTTPException as e:
        raise

    except Exception as e:
        logger.exception(f"Failed to disconnect user: {e}", extra={"user_id": user_data.get("user_id")})
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to disconnect user") from e
