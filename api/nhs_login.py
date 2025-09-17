from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from auth.auth_bearer import get_authenticated_user_data
from crud.user_crud import UserCRUD
from db.session import get_db_session
from models import DeleteAudit, UserDeleteReason, UserStatus
from service.nhs_login_service import NHSLoginService
from service.redis_service import RedisService, get_redis_service

router = APIRouter(prefix="/nhs_login", tags=["NHS Login"])


@router.get("/{app_name}/{app_internal_id}")
async def nhs_login(app_name: str, app_internal_id: str, service: NHSLoginService = Depends()):  # noqa: B008
    url = service.get_nhs_login_url(app_name, app_internal_id)
    return RedirectResponse(url)


@router.get("/callback", response_class=RedirectResponse, status_code=301)
async def nhs_login_callback(request: Request, service: NHSLoginService = Depends()):  # noqa: B008
    req_args = dict(request.query_params)
    deep_link = service.process_callback(req_args)
    return RedirectResponse(deep_link)


@router.post("/logout", response_class=JSONResponse, status_code=200)
async def logout(
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    user_crud: Annotated[UserCRUD, Depends()],
    redis_service: RedisService = Depends(get_redis_service),  # noqa: B008
    db: Session = Depends(get_db_session),  # noqa: B008
):
    user = user_crud.get_user_by_id(user_data["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = UserStatus.LOGOUT.value
    user.status_updated_at = datetime.utcnow()
    user_token = user.token
    db.delete(user_token)
    db.commit()

    # Invalidate user cache on logout
    redis_service.invalidate_user_session(str(user.id))

    return {"message": "User logged out successfully"}


@router.post("/disconnect", response_class=JSONResponse, status_code=200)
async def disconnect(
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    user_crud: Annotated[UserCRUD, Depends()],
    redis_service: RedisService = Depends(get_redis_service),  # noqa: B008
    db: Session = Depends(get_db_session),  # noqa: B008
):
    try:
        user = user_crud.get_user_by_id(user_data["user_id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Invalidate user cache before deletion
        redis_service.invalidate_user_session(str(user.id))

        db.delete(user)

        delete_audit = DeleteAudit(
            user_id=user.id, delete_reason=UserDeleteReason.DISCONNECTED.value
        )
        db.add(delete_audit)
        db.commit()

        return {"message": "User disconnected successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to disconnect user") from e
