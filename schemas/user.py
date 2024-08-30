from typing import Optional
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, field_validator


class UserResponse(BaseModel):
    id: UUID
    first_name: str
    email: str
    gender: str
    age: int
    age_range: str
    postcode: Optional[str]


class NHSUser(BaseModel):
    sub: UUID
    iss: AnyHttpUrl
    aud: str
    nhs_number: int
    birthdate: str
    family_name: str
    identity_proofing_level: str
    email: EmailStr
    email_verified: bool
    given_name: str
    gender: str
    postcode: str


class EmailPreferenceRequest(BaseModel):
    name: str = Field(..., examples=["active10_mailing_list"])

    @field_validator('name')
    def validate_name(cls, name: str) -> str:
        if name != "active10_mailing_list":
            raise ValueError("Invalid name")

        return name
