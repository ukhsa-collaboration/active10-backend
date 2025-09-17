from typing import Any
from uuid import UUID

from pydantic import BaseModel


class WalkingPlanRequestSchema(BaseModel):
    walking_plan_data: dict[str, Any]


class UserWalkingPlanResponseSchema(BaseModel):
    id: UUID
    walking_plan_data: dict[str, Any]
