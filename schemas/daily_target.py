from uuid import UUID

from pydantic import BaseModel, Field


class DailyTargetRequestSchema(BaseModel):
    date: int = Field(..., gt=0)
    daily_target: int = Field(..., gt=0)


class DailyTargetResponseSchema(BaseModel):
    id: UUID
    date: int | None
    daily_target: int
