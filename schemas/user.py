from datetime import date
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, field_validator

from schemas.activity_level import ActivityLevelResponseSchema
from schemas.motivation import UserMotivationResponse


class EmailPreferenceRequest(BaseModel):
    name: str = Field(..., examples=["active10_mailing_list"])

    @field_validator("name")
    def validate_name(cls, name: str) -> str:
        if name != "active10_mailing_list":
            raise ValueError("Invalid name")

        return name


class EmailPreferenceRequestPublic(BaseModel):
    email: EmailStr
    name: str = Field(..., examples=["active10_mailing_list"])


class EmailPreferenceResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool


class UserResponse(BaseModel):
    id: UUID
    first_name: str
    email: str
    gender: str
    age: int
    age_range: str
    postcode: str | None
    identity_level: str | None
    email_preferences: list[EmailPreferenceResponse] | None = []
    latest_motivation: UserMotivationResponse | None = None
    latest_activity_level: ActivityLevelResponseSchema | None = None


class SessionUser(BaseModel):
    user_id: UUID
    keycloak_sub: str
    user_email: str | None = None


class KeycloakUserInfo(BaseModel):
    sub: str
    idp_sub: str
    nhs_number: str
    given_name: str
    identity_proofing_level: str
    birthdate: date
    email: EmailStr
    gender: str = "na"
    postcode: str = "na"

    @field_validator("nhs_number", mode="before")
    @classmethod
    def nhs_number_as_string(cls, value: object) -> object:
        return str(value) if isinstance(value, int) else value


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
