from typing import List  # noqa: I001, UP035

from typing_extensions import Self  # noqa: UP035

from pydantic import BaseModel, Field, model_validator

from schemas.activity import UserActivityRequestSchema


class ActivitiesMigrationsRequestSchema(BaseModel):
    month: int = Field(..., gt=0, description="First date (unix timestamp) of data month")
    activities: List[UserActivityRequestSchema] = Field(...)  # noqa: UP006

    @model_validator(mode="before")
    def check_activities_length(self) -> Self:
        activities = self.get("activities")

        if not 1 <= len(activities) < 32:  # noqa: PLR2004
            raise ValueError("activities list must have between 1 and 31 items")

        return self
