from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from crud.daily_target_crud import UserDailyTargetCRUD
from models import User
from models.daily_target import UserDailyTarget
from schemas.daily_target import DailyTargetRequestSchema, DailyTargetResponseSchema
from service.auth_service import get_authenticated_user_data

router = APIRouter(prefix="/daily_target", tags=["daily target"])


@router.post("/", response_model=DailyTargetResponseSchema, status_code=201)
async def create_daily_target(
        user: Annotated[User, Depends(get_authenticated_user_data)],
        payload: DailyTargetRequestSchema,
        daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    existing_target = daily_target_crud.get_daily_target_by_user_id(user.id)

    if existing_target:
        raise HTTPException(status_code=400, detail="User daily target already exists")

    new_daily_target = UserDailyTarget(
        user_id=user.id,
        daily_target=payload.daily_target
    )
    created_daily_target = daily_target_crud.create_daily_target(new_daily_target)
    return created_daily_target


@router.get("/", response_model=DailyTargetResponseSchema, status_code=200)
async def get_user_daily_target(
        user: Annotated[User, Depends(get_authenticated_user_data)],
        daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    daily_target = daily_target_crud.get_daily_target_by_user_id(user.id)
    if not daily_target:
        raise HTTPException(status_code=404, detail="User daily target not found")
    return daily_target


@router.put("/", response_model=DailyTargetResponseSchema, status_code=200)
async def update_daily_target(
        user: Annotated[User, Depends(get_authenticated_user_data)],
        payload: DailyTargetRequestSchema,
        daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    user_daily_target = daily_target_crud.get_daily_target_by_user_id(user.id)

    if not user_daily_target:
        raise HTTPException(status_code=404, detail="User daily target not found")

    updated_daily_target = daily_target_crud.update_daily_target(user_daily_target, payload)
    return updated_daily_target


@router.delete("/", status_code=204)
async def delete_daily_target(
        user: Annotated[User, Depends(get_authenticated_user_data)],
        daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    user_daily_target = daily_target_crud.get_daily_target_by_user_id(user.id)

    if not user_daily_target:
        raise HTTPException(status_code=404, detail="User daily target not found")

    daily_target_crud.delete_daily_target(user_daily_target)
