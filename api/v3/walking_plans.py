from typing import Annotated

from fastapi import APIRouter, Depends, status

from auth.v3.dependencies import get_current_user
from crud.walking_plan_crud import UserWalkingPlanCRUD
from models.user import User
from models.walking_plan import UserWalkingPlan
from schemas.walking_plan import UserWalkingPlanResponseSchema, WalkingPlanRequestSchema
from utils.custom_exceptions import CustomHTTPException, ErrorCode

router = APIRouter(prefix="/walking_plans", tags=["walking plans"])


def _get_own_walking_plan(crud: UserWalkingPlanCRUD, user: User) -> UserWalkingPlan:
    walking_plan = crud.get_walking_plan_by_user_id(user.id)
    if not walking_plan:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            error_message="User walking plan not found",
        )
    return walking_plan


@router.post("", response_model=UserWalkingPlanResponseSchema, status_code=201)
def create_walking_plan(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: WalkingPlanRequestSchema,
    walking_plan_crud: Annotated[UserWalkingPlanCRUD, Depends()],
):
    if walking_plan_crud.get_walking_plan_by_user_id(current_user.id):
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.ALREADY_EXISTS,
            error_message="User walking plan already exists",
        )

    new_walking_plan = UserWalkingPlan(
        user_id=current_user.id, walking_plan_data=payload.walking_plan_data
    )
    return walking_plan_crud.create_walking_plan(new_walking_plan)


@router.get("", response_model=UserWalkingPlanResponseSchema, status_code=200)
def get_user_walking_plan(
    current_user: Annotated[User, Depends(get_current_user)],
    walking_plan_crud: Annotated[UserWalkingPlanCRUD, Depends()],
):
    return _get_own_walking_plan(walking_plan_crud, current_user)


@router.put("", response_model=UserWalkingPlanResponseSchema, status_code=200)
def update_walking_plan(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: WalkingPlanRequestSchema,
    walking_plan_crud: Annotated[UserWalkingPlanCRUD, Depends()],
):
    walking_plan = _get_own_walking_plan(walking_plan_crud, current_user)
    return walking_plan_crud.update_walking_plan(walking_plan, payload)


@router.delete("", status_code=204)
def delete_walking_plan(
    current_user: Annotated[User, Depends(get_current_user)],
    walking_plan_crud: Annotated[UserWalkingPlanCRUD, Depends()],
):
    walking_plan = _get_own_walking_plan(walking_plan_crud, current_user)
    walking_plan_crud.delete_walking_plan(walking_plan)
