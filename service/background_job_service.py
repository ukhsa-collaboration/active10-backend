from uuid import UUID

from fastapi import HTTPException

from crud.background_job_crud import (
    create_background_job,
    get_background_job,
    update_background_job_status,
)
from schemas.job import JobStatus


def create_job(user_id: str) -> str:
    try:
        user_uuid = UUID(str(user_id))
        background_job = create_background_job(user_id=user_uuid, status=JobStatus.STARTED.value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user id")  # noqa: B904
    except Exception:
        raise HTTPException(status_code=503, detail="Job store unavailable")  # noqa: B904

    return str(background_job.id)


def get_job(job_id: str) -> dict | None:
    try:
        job_uuid = UUID(str(job_id))
    except ValueError:
        return None

    try:
        background_job = get_background_job(job_uuid)
    except Exception:
        raise HTTPException(status_code=503, detail="Job store unavailable")  # noqa: B904

    if not background_job:
        return None

    return {
        "status": background_job.status,
        "user_id": str(background_job.user_id),
        "created_at": int(background_job.created_at.timestamp()),
        "updated_at": int(background_job.updated_at.timestamp()),
    }


def update_job_status(job_id: str, status: str) -> bool:
    try:
        job_uuid = UUID(str(job_id))
    except ValueError:
        return False

    try:
        return update_background_job_status(job_uuid, status)
    except Exception:
        return False
