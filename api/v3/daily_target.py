from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from auth.v3.dependencies import get_current_user
from crud.daily_target_crud import UserDailyTargetCRUD
from models.daily_target import UserDailyTarget
from models.user import User
from schemas.daily_target import DailyTargetRequestSchema, DailyTargetResponseSchema
from utils.custom_exceptions import CustomHTTPException, ErrorCode

router = APIRouter(prefix="/daily_targets", tags=["daily target"])


def _not_found() -> CustomHTTPException:
    return CustomHTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code=ErrorCode.NOT_FOUND,
        error_message="Data not found",
    )


def _get_own_daily_target(
    crud: UserDailyTargetCRUD, target_id: UUID, user: User
) -> UserDailyTarget:
    daily_target = crud.get_user_daily_target_by_id(user_id=user.id, target_id=target_id)
    if not daily_target:
        raise _not_found()
    return daily_target


@router.post("", response_model=DailyTargetResponseSchema, status_code=201)
def create_daily_target(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: DailyTargetRequestSchema,
    daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    if daily_target_crud.get_user_target_by_payload_data(user_id=current_user.id, data=payload):
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.ALREADY_EXISTS,
            error_message="User daily target with same data already exists",
        )

    new_daily_target = UserDailyTarget(
        user_id=current_user.id, date=payload.date, daily_target=payload.daily_target
    )
    return daily_target_crud.create_daily_target(new_daily_target)


@router.get("", response_model=list[DailyTargetResponseSchema], status_code=200)
def get_user_daily_targets_list(  # noqa: PLR0913
    current_user: Annotated[User, Depends(get_current_user)],
    daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
    date: int | None = Query(None, description="Filter by exact date (UNIX timestamp)"),
    start_date: int | None = Query(None, description="Filter by start date (UNIX timestamp)"),
    end_date: int | None = Query(None, description="Filter by end date (UNIX timestamp)"),
    min_daily_target: int | None = Query(None, description="Filter by minimum daily target"),
    max_daily_target: int | None = Query(None, description="Filter by maximum daily target"),
):
    filters = {
        "date": date,
        "start_date": start_date,
        "end_date": end_date,
        "min_daily_target": min_daily_target,
        "max_daily_target": max_daily_target,
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    daily_targets = daily_target_crud.get_daily_targets_by_filters(current_user.id, filters)
    if not daily_targets:
        raise _not_found()
    return daily_targets


@router.get("/{target_id}", response_model=DailyTargetResponseSchema, status_code=200)
def get_user_daily_target(
    target_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    return _get_own_daily_target(daily_target_crud, target_id, current_user)


@router.put("/{target_id}", response_model=DailyTargetResponseSchema, status_code=200)
def update_daily_target(
    target_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    payload: DailyTargetRequestSchema,
    daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    daily_target = _get_own_daily_target(daily_target_crud, target_id, current_user)
    return daily_target_crud.update_daily_target(daily_target, payload)


@router.delete("/{target_id}", status_code=204)
def delete_daily_target(
    target_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    daily_target_crud: Annotated[UserDailyTargetCRUD, Depends()],
):
    daily_target = _get_own_daily_target(daily_target_crud, target_id, current_user)
    daily_target_crud.delete_daily_target(daily_target)
