from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException

from schemas.job import JobStatus, JobStatusResponseSchema
from service import background_job_service
from utils.base_config import logger


async def run_tracked_job(
    job_id: str,
    tracked_coro: Callable[..., Awaitable[None]],
    *args: Any,
    **kwargs: Any,
) -> None:
    try:
        await tracked_coro(*args, **kwargs)
        background_job_service.update_job_status(job_id, JobStatus.QUEUED.value)
    except Exception:
        background_job_service.update_job_status(job_id, JobStatus.FAILED.value)
        logger.exception("Tracked background job failed", extra={"job_id": job_id})
        raise


def get_job_status_for_user(job_id: str, user_id: str) -> JobStatusResponseSchema:
    job = background_job_service.get_job(job_id)

    if not job or str(job.get("user_id")) != str(user_id):
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponseSchema(
        job_id=job_id,
        status=job.get("status", JobStatus.STARTED.value),
        created_at=job.get("created_at", 0),
        updated_at=job.get("updated_at", 0),
    )
