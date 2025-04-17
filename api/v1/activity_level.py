from typing import Annotated, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from auth.auth_bearer import get_authenticated_user_data
from models import User
from models.activity_level import UserActivityLevel
from schemas.activity_level import ActivityLevelResponseSchema, ActivityLevelRequestSchema
from crud.activity_level_crud import get_all_user_activity_levels, get_user_activity_level_by_id, create_user_activity_level, update_user_activity_level

router = APIRouter(prefix="/activity_level", tags=["activity level"])


@router.get("/", response_model=List[ActivityLevelResponseSchema], status_code=200)
async def get_user_activity_levels_list(
        user: Annotated[User, Depends(get_authenticated_user_data)],
):

    activity_levels = get_all_user_activity_levels(user.id)

    return activity_levels


@router.get("/{activity_level_id}", response_model=ActivityLevelResponseSchema, status_code=200)
async def get_user_activity_level(
        activity_level_id: UUID,
        user: Annotated[User, Depends(get_authenticated_user_data)]
):
    activity_level = get_user_activity_level_by_id(user.id, activity_level_id)

    if not activity_level:
        raise HTTPException(status_code=404, detail="Data not found")

    return activity_level


@router.post("/", response_model=ActivityLevelResponseSchema, status_code=200)
async def create_activity_level(
        user: Annotated[User, Depends(get_authenticated_user_data)],
        activity_level: ActivityLevelRequestSchema,
):
    """
    Create a new activity level entry for current user.

    Activity Levels:
    - Inactive
    - Moderately active
    - Active
    """
    valid_levels = ["Inactive", "Moderately active", "Active"]
    if activity_level.level not in valid_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid activity level. Must be one of: {', '.join(valid_levels)}"
        )

    activity_level_date = activity_level.date
    if activity_level_date is None:
        activity_level_date = int(datetime.now().timestamp())

    user_activity_level = UserActivityLevel(
        user_id=user.id,
        date=activity_level_date,
        level=activity_level.level
    )
    _ = create_user_activity_level(user_activity_level)
    return user_activity_level


@router.put("/{activity_level_id}", response_model=ActivityLevelResponseSchema, status_code=200)
async def update_activity_level(
        activity_level_id: UUID,
        user: Annotated[User, Depends(get_authenticated_user_data)],
        activity_level: ActivityLevelRequestSchema,
):
    """
    Update an existing activity level entry for current user.

    Activity Levels:
    - Inactive
    - Moderately active
    - Active
    """
    valid_levels = ["Inactive", "Moderately active", "Active"]
    if activity_level.level not in valid_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid activity level. Must be one of: {', '.join(valid_levels)}"
        )

    activity_level_date = activity_level.date
    if activity_level_date is None:
        activity_level_date = int(datetime.now().timestamp())

    user_activity_level = UserActivityLevel(
        user_id=user.id,
        date=activity_level_date,
        level=activity_level.level
    )
    updated_activity_level = update_user_activity_level(activity_level_id, user_activity_level)
    if not updated_activity_level:
        raise HTTPException(status_code=404, detail="Activity level not found")
    return updated_activity_level