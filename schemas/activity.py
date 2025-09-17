from typing import Any
from uuid import UUID

from pydantic import BaseModel


class Activity(BaseModel):
    brisk_minutes: int
    walking_minutes: int
    steps: int


class UserActivityRequestSchema(BaseModel):
    date: int
    user_postcode: str
    user_age_range: str
    rewards: list[dict[str, Any]] | None = []
    activity: Activity


class ActivityResponseSchema(BaseModel):
    id: UUID
    date: int
    user_postcode: str
    user_age_range: str
    brisk_minutes: int
    walking_minutes: int
    steps: int
    rewards: list[dict[str, Any]] | None = []
    user_id: UUID
