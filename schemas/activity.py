from pydantic import BaseModel
from typing import List, Optional


class Reward(BaseModel):
    earned: int
    slug: str


class Activity(BaseModel):
    minsBrisk: int
    minsWalking: int
    steps: int


class UserActivityRequestSchema(BaseModel):
    date: int
    user_postcode: str
    user_age_range: str
    rewards: Optional[List[Reward]] = []
    activity: Activity
