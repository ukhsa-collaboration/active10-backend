from typing import Optional

from pydantic import BaseModel, Field
from uuid import UUID


class DailyTargetRequestSchema(BaseModel):
    date: int = Field(..., gt=0)
    daily_target: int = Field(..., gt=0)


class DailyTargetResponseSchema(BaseModel):
    id: UUID
    date: Optional[int]
    daily_target: int
