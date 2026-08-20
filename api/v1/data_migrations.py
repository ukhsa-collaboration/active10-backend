import calendar
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from starlette.responses import JSONResponse

from auth.auth_bearer import get_authenticated_user_data
from schemas.job import JobStatus, JobStatusResponseSchema
from schemas.migrations_schema import ActivitiesMigrationsRequestSchema
from service import background_job_service
from service.migrations_service import publish_bulk_activities_data_to_sns
from utils.background_jobs import get_job_status_for_user, run_tracked_job

router = APIRouter(prefix="/migrations", tags=["migrations"])


@router.post("/activities", status_code=202, response_class=JSONResponse)
async def save_bulk_activities(
    request: Request,
    background_task: BackgroundTasks,
    data: ActivitiesMigrationsRequestSchema,
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
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

    out_of_range_activities = [
        activity
        for activity in data.activities
        if not unix_month_start <= activity.date <= unix_month_end
    ]

    if out_of_range_activities:
        raise HTTPException(status_code=400, detail="Some activities are out of the month range")

    job_id = background_job_service.create_job(user_data["user_id"])

    background_task.add_task(
        run_tracked_job,
        job_id,
        publish_bulk_activities_data_to_sns,
        data,
        user_data["user_id"],
    )

    status_url = str(request.url_for("v1_migration_activity_job_status", job_id=job_id))
    return JSONResponse(
        status_code=202,
        headers={"Location": status_url},
        content={
            "job_id": job_id,
            "status": JobStatus.STARTED.value,
            "status_url": status_url,
        },
    )


@router.get(
    "/activities/{job_id}/status",
    response_model=JobStatusResponseSchema,
    name="v1_migration_activity_job_status",
)
async def get_migration_job_status(
    job_id: str,
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
):
    return get_job_status_for_user(job_id=job_id, user_id=user_data["user_id"])
