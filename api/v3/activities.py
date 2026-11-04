from datetime import datetime, timezone
from typing import Annotated

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import JSONResponse

from auth.v3.dependencies import get_current_user
from crud.activities_crud import get_activities_by_filters
from models.user import User
from schemas.activity import ActivityResponseSchema, UserActivityRequestSchema
from service.activity_service import load_activities_data_in_sns
from utils.custom_exceptions import CustomHTTPException, ErrorCode

router = APIRouter(prefix="/activities", tags=["activities"])

ONE_YEAR_IN_SECONDS = 31536000


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
    date: int | None = Query(None, gt=0, description="Filter by exact date (UNIX timestamp)"),
    start_date: int | None = Query(None, gt=0, description="Filter by start date (UNIX timestamp)"),
    end_date: int | None = Query(None, gt=0, description="Filter by end date (UNIX timestamp)"),
):
    if date and (start_date or end_date):
        raise _invalid_request("Cannot use date filter with start_date or end_date filters")

    if (start_date and not end_date) or (end_date and not start_date):
        raise _invalid_request("Both start_date and end_date filters must be used together")

    if start_date and end_date:
        if start_date > end_date:
            raise _invalid_request("Start date cannot be greater than end date")
        if end_date - start_date > ONE_YEAR_IN_SECONDS:
            raise _invalid_request("Date range cannot be greater than 1 year")

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
