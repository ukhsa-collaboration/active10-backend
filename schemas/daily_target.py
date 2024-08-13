from pydantic import BaseModel
from uuid import UUID


class DailyTargetRequestSchema(BaseModel):
    daily_target: int


class DailyTargetResponseSchema(BaseModel):
    id: UUID
    daily_target: int
