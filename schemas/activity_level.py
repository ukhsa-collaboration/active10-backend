from typing import Optional

from pydantic import BaseModel, Field
from uuid import UUID


class ActivityLevelRequestSchema(BaseModel):
    date: Optional[int] = Field(default=None, gt=0)
    level: str = Field(...)


class ActivityLevelResponseSchema(BaseModel):
    id: UUID
    date: int
    level: str
    created_at: int
    updated_at: int
