from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from auth.auth_bearer import get_authenticated_user_data
from crud.daily_target_crud import UserDailyTargetCRUD
from models import User
from models.daily_target import UserDailyTarget
from schemas.daily_target import DailyTargetRequestSchema, DailyTargetResponseSchema


router = APIRouter(prefix="/daily_targets", tags=["daily target"])


@router.post("", response_model=DailyTargetResponseSchema, status_code=201)
async def create_daily_target(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    payload: DailyTargetRequestSchema,
    daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    existing_target = daily_target_crud.get_user_target_by_payload_data(
        user_id=user.id, data=payload
    )

    if existing_target:
        raise HTTPException(
            status_code=400, detail="User daily target with same data already exists"
        )

    new_daily_target = UserDailyTarget(
        user_id=user.id, date=payload.date, daily_target=payload.daily_target
    )
    created_daily_target = daily_target_crud.create_daily_target(new_daily_target)
    return created_daily_target


@router.get("", response_model=List[DailyTargetResponseSchema], status_code=200)
async def get_user_daily_targets_list(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
    date: Optional[int] = Query(
        None, description="Filter by exact date (UNIX timestamp)"
    ),
    start_date: Optional[int] = Query(
        None, description="Filter by start date (UNIX timestamp)"
    ),
    end_date: Optional[int] = Query(
        None, description="Filter by end date (UNIX timestamp)"
    ),
    min_daily_target: Optional[int] = Query(
        None, description="Filter by minimum daily target"
    ),
    max_daily_target: Optional[int] = Query(
        None, description="Filter by maximum daily target"
    ),
):
    filters = {
        "date": date,
        "start_date": start_date,
        "end_date": end_date,
        "min_daily_target": min_daily_target,
        "max_daily_target": max_daily_target,
    }

    filters = {k: v for k, v in filters.items() if v is not None}

    daily_targets = daily_target_crud.get_daily_targets_by_filters(user.id, filters)

    if not daily_targets:
        raise HTTPException(status_code=404, detail="Data not found")

    return daily_targets


@router.get("/{target_id}", response_model=DailyTargetResponseSchema, status_code=200)
async def get_user_daily_target(
    target_id: UUID,
    user: Annotated[User, Depends(get_authenticated_user_data)],
    daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    daily_target = daily_target_crud.get_user_daily_target_by_id(
        user_id=user.id, target_id=target_id
    )

    if not daily_target:
        raise HTTPException(status_code=404, detail="Data not found")

    return daily_target


@router.put("/{target_id}", response_model=DailyTargetResponseSchema, status_code=200)
async def update_daily_target(
    target_id: UUID,
    user: Annotated[User, Depends(get_authenticated_user_data)],
    payload: DailyTargetRequestSchema,
    daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    user_daily_target = daily_target_crud.get_user_daily_target_by_id(
        user_id=user.id, target_id=target_id
    )

    if not user_daily_target:
        raise HTTPException(status_code=404, detail="Data not found")

    updated_daily_target = daily_target_crud.update_daily_target(
        user_daily_target, payload
    )
    return updated_daily_target


@router.delete("/{target_id}", status_code=204)
async def delete_daily_target(
    target_id: UUID,
    user: Annotated[User, Depends(get_authenticated_user_data)],
    daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    user_daily_target = daily_target_crud.get_user_daily_target_by_id(
        user_id=user.id, target_id=target_id
    )

    if not user_daily_target:
        raise HTTPException(status_code=404, detail="Data not found")

    daily_target_crud.delete_daily_target(user_daily_target)
