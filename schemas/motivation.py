from typing import List
from uuid import UUID
from pydantic import BaseModel, Field


class GoalItem(BaseModel):
    text: str = Field(..., examples=["I want to make regular walks a part of my lifestyle"])
    id: int = Field(..., examples=["1"])


class CreateUpdateUserMotivationRequest(BaseModel):
    goals: List[GoalItem]


class UserMotivationResponse(BaseModel):
    id: UUID
    user_id: UUID
    created_at: int
    goals: List[GoalItem]
