from datetime import datetime

from fastapi.responses import JSONResponse
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from auth.auth_bearer import get_authenticated_user_data
from db.session import get_db_session
from models import UserStatus, User, DeleteAudit, UserDeleteReason

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/logout/", response_class=JSONResponse, status_code=200)
async def logout(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    db: Session = Depends(get_db_session)
):
    user.status = UserStatus.LOGOUT.value
    user.status_updated_at = datetime.utcnow()
    user.current_token = None
    db.commit()

    return {"message": "User logged out successfully"}


@router.get("/disconnect/", response_class=JSONResponse, status_code=200)
async def disconnect(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    db: Session = Depends(get_db_session)
):
    try:
        db.delete(user)

        delete_audit = DeleteAudit(
            user_id = user.id,
            delete_reason = UserDeleteReason.DISCONNECTED.value
        )
        db.add(delete_audit)
        db.commit()

        return {"message": "User disconnected successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to disconnect user") from e
