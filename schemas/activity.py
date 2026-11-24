from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self  # noqa: UP035


class Activity(BaseModel):
    brisk_minutes: int
    walking_minutes: int
    steps: int
    effort: int | None = Field(None, ge=1, le=10)
    feeling: int | None = Field(None, ge=0, le=2)

    @model_validator(mode="after")
    def clear_feeling_without_effort(self) -> Self:
        if self.effort is None:
            self.feeling = None

        return self


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
    effort: int | None = None
    feeling: int | None = None
    rewards: list[dict[str, Any]] | None = []
    user_id: UUID
