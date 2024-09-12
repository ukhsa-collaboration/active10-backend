from uuid import UUID

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class Activity(BaseModel):
    brisk_minutes: int
    walking_minutes: int
    steps: int


class UserActivityRequestSchema(BaseModel):
    date: int
    user_postcode: str
    user_age_range: str
    rewards: Optional[List[Dict[str, Any]]] = []
    activity: Activity


class ActivityResponseSchema(BaseModel):
    id: UUID
    date: int
    user_postcode: str
    user_age_range: str
    brisk_minutes: int
    walking_minutes: int
    steps: int
    rewards: Optional[List[Dict[str, Any]]] = []
    user_id: UUID
