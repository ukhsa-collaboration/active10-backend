from uuid import UUID

from pydantic import BaseModel


class Activity(BaseModel):
    user_id: UUID
    date: int
    mins_brisk: int
    mins_walking: int
    steps: int
