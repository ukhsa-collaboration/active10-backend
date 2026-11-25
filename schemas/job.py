from enum import Enum

from pydantic import BaseModel


class JobStatus(str, Enum):
    STARTED = "started"
    QUEUED = "queued"
    FAILED = "failed"


class JobStatusResponseSchema(BaseModel):
    job_id: str
    status: str
    created_at: int
    updated_at: int
