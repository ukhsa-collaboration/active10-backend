from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from auth.v3.dependencies import get_current_user
from crud.activity_level_crud import UserActivityLevelCRUD
from models.activity_level import UserActivityLevel
from models.user import User
from schemas.activity_level import ActivityLevelRequestSchema, ActivityLevelResponseSchema
from utils.custom_exceptions import CustomHTTPException, ErrorCode

router = APIRouter(prefix="/activity_level", tags=["activity level"])


def _get_own_activity_level(
    crud: UserActivityLevelCRUD, activity_level_id: UUID, user: User
) -> UserActivityLevel:
    activity_level = crud.get_by_id(user.id, activity_level_id)
    if not activity_level:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            error_message="Data not found",
        )
    return activity_level


@router.get("/", response_model=list[ActivityLevelResponseSchema], status_code=200)
def get_user_activity_levels_list(
    current_user: Annotated[User, Depends(get_current_user)],
    crud: Annotated[UserActivityLevelCRUD, Depends()],
):
    return crud.get_all_by_user(current_user.id)


@router.get("/{activity_level_id}", response_model=ActivityLevelResponseSchema, status_code=200)
def get_user_activity_level(
    activity_level_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    crud: Annotated[UserActivityLevelCRUD, Depends()],
):
    return _get_own_activity_level(crud, activity_level_id, current_user)


@router.post("/", response_model=ActivityLevelResponseSchema, status_code=200)
def create_activity_level(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: ActivityLevelRequestSchema,
    crud: Annotated[UserActivityLevelCRUD, Depends()],
):
    return crud.create(current_user.id, payload=payload)


@router.put("/{activity_level_id}", response_model=ActivityLevelResponseSchema, status_code=200)
def update_activity_level(
    activity_level_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    payload: ActivityLevelRequestSchema,
    crud: Annotated[UserActivityLevelCRUD, Depends()],
):
    activity_level = _get_own_activity_level(crud, activity_level_id, current_user)
    return crud.update(activity_level, payload)


@router.delete("/{activity_level_id}", status_code=204)
def delete_activity_level(
    activity_level_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    crud: Annotated[UserActivityLevelCRUD, Depends()],
):
    activity_level = _get_own_activity_level(crud, activity_level_id, current_user)
    crud.delete(activity_level)
