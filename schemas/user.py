from typing import Optional
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, EmailStr


class UserResponse(BaseModel):
    id: UUID
    first_name: str
    email: str
    gender: str
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
