from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

ALLOWED_ACTIVITY_LEVELS = {"Active", "Moderately Active", "Inactive"}


class ActivityLevelRequestSchema(BaseModel):
    level: Literal["Active", "Moderately Active", "Inactive"] = Field(
        ..., description="User's activity level", examples=["Active"]
    )

    @field_validator("level")
    def validate_level(cls, value: str) -> str:
        if value not in ALLOWED_ACTIVITY_LEVELS:
            raise ValueError(f"Level must be one of: {', '.join(ALLOWED_ACTIVITY_LEVELS)}")
        return value


class ActivityLevelResponseSchema(BaseModel):
    id: UUID
    level: str
    created_at: int
    updated_at: int
