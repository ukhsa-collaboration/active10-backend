from typing import Annotated
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from models import User
from schemas.migrations_schema import ActivitiesMigrationsRequestSchema
from service.auth_service import get_authenticated_user_data
from service.migrations_service import load_bulk_activities_data
from datetime import datetime
import calendar

router = APIRouter(prefix="/migrations", tags=["migrations"])


@router.post("/activities/", status_code=201)
async def save_bulk_activities(
        background_task: BackgroundTasks,
        data: ActivitiesMigrationsRequestSchema,
        user: Annotated[User, Depends(get_authenticated_user_data)]
):
    month_start = datetime.fromtimestamp(data.month).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = month_start.replace(
        day=calendar.monthrange(month_start.year, month_start.month)[1],
        hour=23, minute=59, second=59, microsecond=999999
    )

    unix_month_start = int(month_start.timestamp())
    unix_month_end = int(month_end.timestamp())

    out_of_range_activities = [
        activity for activity in data.activities if not unix_month_start <= activity.date <= unix_month_end
    ]

    if out_of_range_activities:
        raise HTTPException(
            status_code=400,
            detail="Some activities are out of the month range"
        )

    background_task.add_task(load_bulk_activities_data, data, user)

    return {"message": "Success"}
