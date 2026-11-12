from datetime import datetime, timezone
from typing import Annotated

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import JSONResponse
from utils.date_filters import validate_date_filters

from auth.v3.dependencies import get_current_user
from crud.activities_crud import get_activities_by_filters
from models.user import User
from schemas.activity import ActivityResponseSchema, UserActivityRequestSchema
from service.activity_service import load_activities_data_in_sns
from utils.custom_exceptions import CustomHTTPException, ErrorCode

router = APIRouter(prefix="/activities", tags=["activities"])


def _invalid_request(message: str) -> CustomHTTPException:
    return CustomHTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code=ErrorCode.INVALID_REQUEST,
        error_message=message,
    )


@router.post("", status_code=201, response_class=JSONResponse)
async def save_activity(
    background_task: BackgroundTasks,
    activity_payload: UserActivityRequestSchema,
    current_user: Annotated[User, Depends(get_current_user)],
):
    background_task.add_task(load_activities_data_in_sns, activity_payload, current_user.id)
    return {"message": "Success"}


@router.get("", response_model=list[ActivityResponseSchema], status_code=200)
def list_activities(
    current_user: Annotated[User, Depends(get_current_user)],
    date: Annotated[
        int | None, Query(gt=0, description="Filter by exact date (UNIX timestamp)")
    ] = None,
    start_date: Annotated[
        int | None, Query(gt=0, description="Filter by start date (UNIX timestamp)")
    ] = None,
    end_date: Annotated[
        int | None, Query(gt=0, description="Filter by end date (UNIX timestamp)")
    ] = None,
):
    try:
        validate_date_filters(date, start_date, end_date)
    except ValueError as e:
        raise _invalid_request(str(e)) from e

    if not date and not start_date and not end_date:
        start_date = int(
            (datetime.now(timezone.utc).replace(tzinfo=None) - relativedelta(years=1)).timestamp()  # noqa: UP017 Not supported in Python 3.10
        )

    filters = {
        key: value
        for key, value in {"date": date, "start_date": start_date, "end_date": end_date}.items()
        if value is not None
    }
    activities = get_activities_by_filters(user_id=current_user.id, filters=filters)
    if not activities:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            error_message="Data not found",
        )
    return activities
