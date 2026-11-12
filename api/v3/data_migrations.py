import calendar
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse

from auth.v3.dependencies import get_current_user
from models.user import User
from schemas.migrations_schema import ActivitiesMigrationsRequestSchema
from service.migrations_service import publish_bulk_activities_data_to_sns
from utils.custom_exceptions import CustomHTTPException, ErrorCode

router = APIRouter(prefix="/migrations", tags=["migrations"])


@router.post("/activities", status_code=201, response_class=JSONResponse)
async def save_bulk_activities(
    background_task: BackgroundTasks,
    data: ActivitiesMigrationsRequestSchema,
    current_user: Annotated[User, Depends(get_current_user)],
):
    month_start = datetime.fromtimestamp(data.month).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    month_end = month_start.replace(
        day=calendar.monthrange(month_start.year, month_start.month)[1],
        hour=23,
        minute=59,
        second=59,
        microsecond=999999,
    )
    unix_month_start = int(month_start.timestamp())
    unix_month_end = int(month_end.timestamp())

    if any(not unix_month_start <= a.date <= unix_month_end for a in data.activities):
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.INVALID_REQUEST,
            error_message="Some activities are out of the month range",
        )

    background_task.add_task(publish_bulk_activities_data_to_sns, data, current_user.id)
    return {"message": "Success"}
