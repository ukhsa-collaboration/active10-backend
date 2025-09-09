from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from auth.auth_bearer import get_authenticated_user_data
from crud.walking_plan_crud import UserWalkingPlanCRUD
from models import User
from models.walking_plan import UserWalkingPlan
from schemas.walking_plan import WalkingPlanRequestSchema, UserWalkingPlanResponseSchema

router = APIRouter(prefix="/walking_plans", tags=["walking plans"])


@router.post("", response_model=UserWalkingPlanResponseSchema, status_code=201)
async def create_walking_plan(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    payload: WalkingPlanRequestSchema,
    walking_plan_crud: Annotated[UserWalkingPlanCRUD, Depends()],
):
    existing_plan = walking_plan_crud.get_walking_plan_by_user_id(user.id)

    if existing_plan:
        raise HTTPException(status_code=400, detail="User walking plan already exists")

    new_walking_plan = UserWalkingPlan(
        user_id=user.id, walking_plan_data=payload.walking_plan_data
    )
    created_walking_plan = walking_plan_crud.create_walking_plan(new_walking_plan)
    return created_walking_plan


@router.get("", response_model=UserWalkingPlanResponseSchema, status_code=200)
async def get_user_walking_plan(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    walking_plan_crud: Annotated[UserWalkingPlanCRUD, Depends()],
):
    walking_plan = walking_plan_crud.get_walking_plan_by_user_id(user.id)
    if not walking_plan:
        raise HTTPException(status_code=404, detail="User walking plan not found")
    return walking_plan


@router.put("", response_model=UserWalkingPlanResponseSchema, status_code=200)
async def update_walking_plan(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    payload: WalkingPlanRequestSchema,
    walking_plan_crud: Annotated[UserWalkingPlanCRUD, Depends()],
):
    user_walking_plan = walking_plan_crud.get_walking_plan_by_user_id(user.id)

    if not user_walking_plan:
        raise HTTPException(status_code=404, detail="User walking plan not found")

    updated_walking_plan = walking_plan_crud.update_walking_plan(
        user_walking_plan, payload
    )
    return updated_walking_plan


@router.delete("", status_code=204)
async def delete_walking_plan(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    walking_plan_crud: Annotated[UserWalkingPlanCRUD, Depends()],
):
    user_walking_plan = walking_plan_crud.get_walking_plan_by_user_id(user.id)

    if not user_walking_plan:
        raise HTTPException(status_code=404, detail="User walking plan not found")

    walking_plan_crud.delete_walking_plan(user_walking_plan)
