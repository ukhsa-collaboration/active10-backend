import calendar
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from starlette.responses import JSONResponse

from auth.auth_bearer import get_authenticated_user_data
from crud.activities_crud import ActivityCrud
from models import User
from schemas.migrations_schema import ActivitiesMigrationsRequestSchema
from service.migrations_service import load_bulk_activities_data

router = APIRouter(prefix="/migrations", tags=["migrations"])


@router.post("/activities/", status_code=201, response_class=JSONResponse)
async def save_bulk_activities(
        background_task: BackgroundTasks,
        activities_crud: Annotated[ActivityCrud, Depends()],
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

    background_task.add_task(load_bulk_activities_data, data, str(user.id))
    activities_crud.create_bulk_activities(data.activities, user_id=user.id)

    return {"message": "Success"}
