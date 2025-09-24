from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from auth.auth_bearer import get_authenticated_user_data
from crud.activity_level_crud import UserActivityLevelCRUD
from schemas.activity_level import ActivityLevelRequestSchema, ActivityLevelResponseSchema

router = APIRouter(prefix="/activity_level", tags=["activity level"])


@router.get("/", response_model=list[ActivityLevelResponseSchema], status_code=200)
async def get_user_activity_levels_list(
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    crud: Annotated[UserActivityLevelCRUD, Depends()],
):
    activity_levels = crud.get_all_by_user(user_data["user_id"])

    return activity_levels


@router.get("/{activity_level_id}", response_model=ActivityLevelResponseSchema, status_code=200)
async def get_user_activity_level(
    activity_level_id: UUID,
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    crud: Annotated[UserActivityLevelCRUD, Depends()],
):
    activity_level = crud.get_by_id(user_data["user_id"], activity_level_id)

    if not activity_level:
        raise HTTPException(status_code=404, detail="Data not found")

    return activity_level


@router.post("/", response_model=ActivityLevelResponseSchema, status_code=200)
async def create_activity_level(
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    payload: ActivityLevelRequestSchema,
    crud: Annotated[UserActivityLevelCRUD, Depends()],
):
    new_activity_level = crud.create(user_data["user_id"], payload=payload)
    return new_activity_level


@router.put("/{activity_level_id}", response_model=ActivityLevelResponseSchema, status_code=200)
async def update_activity_level(
    activity_level_id: UUID,
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    payload: ActivityLevelRequestSchema,
    crud: Annotated[UserActivityLevelCRUD, Depends()],
):
    existing_level = crud.get_by_id(user_data["user_id"], activity_level_id)
    if not existing_level:
        raise HTTPException(status_code=404, detail="Data not found")

    activity_level = crud.update(existing_level, payload)
    return activity_level


@router.delete("/{activity_level_id}", status_code=204)
async def delete_activity_level(
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    activity_level_id: UUID,
    crud: Annotated[UserActivityLevelCRUD, Depends()],
):
    existing_level = crud.get_by_id(user_data["user_id"], activity_level_id)
    if not existing_level:
        raise HTTPException(status_code=404, detail="Data not found")

    crud.delete(existing_level)
