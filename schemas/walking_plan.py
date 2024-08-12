from typing import Dict, Any

from pydantic import BaseModel
from uuid import UUID


class WalkingPlanRequestSchema(BaseModel):
    walking_plan_data: Dict[str, Any]


class UserWalkingPlanResponseSchema(BaseModel):
    id: UUID
    walking_plan_data: Dict[str, Any]
