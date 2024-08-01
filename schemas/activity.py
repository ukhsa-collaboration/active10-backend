from pydantic import BaseModel


class Activity(BaseModel):
    user_id: int
    date: int
    mins_brisk: int
    mins_walking: int
    steps: int
