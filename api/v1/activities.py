from datetime import datetime, timezone
from typing import Annotated

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from auth.auth_bearer import get_authenticated_user_data
from crud.activities_crud import get_activities_by_filters
from schemas.activity import ActivityResponseSchema, UserActivityRequestSchema
from schemas.job import JobStatus, JobStatusResponseSchema
from service import background_job_service
from service.activity_service import load_activities_data_in_sns
from utils.background_jobs import get_job_status_for_user, run_tracked_job

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post("", status_code=202, response_class=JSONResponse)
async def save_activity(
    request: Request,
    background_task: BackgroundTasks,
    activity_payload: UserActivityRequestSchema,
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
):
    job_id = background_job_service.create_job(user_data["user_id"])
    background_task.add_task(
        run_tracked_job,
        job_id,
        load_activities_data_in_sns,
        activity_payload,
        user_data["user_id"],
    )

    status_url = str(request.url_for("v1_activity_job_status", job_id=job_id))
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
    "/{job_id}/status",
    response_model=JobStatusResponseSchema,
    name="v1_activity_job_status",
)
async def get_activity_job_status(
    job_id: str,
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
):
    return get_job_status_for_user(job_id=job_id, user_id=user_data["user_id"])


@router.get("", response_model=list[ActivityResponseSchema], status_code=200)
def list_activities(
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    date: int | None = Query(None, gt=0, description="Filter by exact date (UNIX timestamp)"),
    start_date: int | None = Query(None, gt=0, description="Filter by start date (UNIX timestamp)"),
    end_date: int | None = Query(None, gt=0, description="Filter by end date (UNIX timestamp)"),
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
            raise HTTPException(status_code=400, detail="Date range cannot be greater than 1 year")

    if not date and not start_date and not end_date:
        start_date = int(
            (datetime.now(timezone.utc).replace(tzinfo=None) - relativedelta(years=1)).timestamp()  # noqa: UP017 Not supported in Python 3.10
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

    activities = get_activities_by_filters(user_id=user_data["user_id"], filters=filters)

    if not activities:
        raise HTTPException(status_code=404, detail="Data not found")

    return activities
