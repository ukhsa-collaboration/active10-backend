from datetime import datetime, timezone
from typing import Annotated, Optional, List

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, BackgroundTasks, Query, HTTPException

from auth.auth_bearer import get_authenticated_user_data
from crud.activities_crud import create_activity, get_activities_by_filters
from models import User
from schemas.activity import UserActivityRequestSchema, ActivityResponseSchema
from service.activity_service import load_activity_data

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post("/", status_code=201, response_model=ActivityResponseSchema)
async def save_activity(
    background_task: BackgroundTasks,
    activity_payload: UserActivityRequestSchema,
    user: Annotated[User, Depends(get_authenticated_user_data)],
):
    background_task.add_task(load_activity_data, activity_payload, str(user.id))
    activity = create_activity(activity_payload, user_id=user.id)

    return activity


@router.get("/", response_model=List[ActivityResponseSchema], status_code=200)
async def list_activities(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    date: Optional[int] = Query(
        None, gt=0, description="Filter by exact date (UNIX timestamp)"
    ),
    start_date: Optional[int] = Query(
        None, gt=0, description="Filter by start date (UNIX timestamp)"
    ),
    end_date: Optional[int] = Query(
        None, gt=0, description="Filter by end date (UNIX timestamp)"
    ),
):
    if date and (start_date or end_date):
        raise HTTPException(
            status_code=400,
            detail="Cannot use date filter with start_date or end_date filters",
        )

    if (start_date and not end_date) or (end_date and not start_date):
        raise HTTPException(
            status_code=400,
            detail="Both start_date and end_date filters must be used together",
        )

    if start_date and end_date:
        if start_date > end_date:
            raise HTTPException(
                status_code=400, detail="Start date cannot be greater than end date"
            )

        unix_one_year = 31536000

        if end_date - start_date > unix_one_year:
            raise HTTPException(
                status_code=400, detail="Date range cannot be greater than 1 year"
            )

    if not date and not start_date and not end_date:
        start_date = int(
            (
                datetime.now(timezone.utc).replace(tzinfo=None) - relativedelta(years=1)
            ).timestamp()
        )

    filters = {
        k: v
        for k, v in {
            "date": date,
            "start_date": start_date,
            "end_date": end_date,
        }.items()
        if v is not None
    }

    activities = get_activities_by_filters(user_id=user.id, filters=filters)

    if not activities:
        raise HTTPException(status_code=404, detail="Data not found")

    return activities
