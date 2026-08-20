from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse

from auth.auth_bearer import get_authenticated_user_data
from schemas.activity import UserActivityRequestSchema
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

    status_url = str(request.url_for("v2_activity_job_status", job_id=job_id))
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
    name="v2_activity_job_status",
)
async def get_activity_job_status(
    job_id: str,
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
):
    return get_job_status_for_user(job_id=job_id, user_id=user_data["user_id"])
