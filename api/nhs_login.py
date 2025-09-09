from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from auth.auth_bearer import get_authenticated_user_data
from db.session import get_db_session
from models import User, UserStatus, UserDeleteReason, DeleteAudit
from service.nhs_login_service import NHSLoginService

router = APIRouter(prefix="/nhs_login", tags=["NHS Login"])


@router.get("/{app_name}/{app_internal_id}")
async def nhs_login(
    app_name: str, app_internal_id: str, service: NHSLoginService = Depends()
):
    url = service.get_nhs_login_url(app_name, app_internal_id)
    return RedirectResponse(url)


@router.get("/callback", response_class=RedirectResponse, status_code=301)
async def nhs_login_callback(request: Request, service: NHSLoginService = Depends()):
    req_args = dict(request.query_params)
    deep_link = service.process_callback(req_args)
    return RedirectResponse(deep_link)


@router.post("/logout", response_class=JSONResponse, status_code=200)
async def logout(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    db: Session = Depends(get_db_session),
):
    user.status = UserStatus.LOGOUT.value
    user.status_updated_at = datetime.utcnow()
    user_token = user.token
    db.delete(user_token)
    db.commit()

    return {"message": "User logged out successfully"}


@router.post("/disconnect", response_class=JSONResponse, status_code=200)
async def disconnect(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    db: Session = Depends(get_db_session),
):
    try:
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
