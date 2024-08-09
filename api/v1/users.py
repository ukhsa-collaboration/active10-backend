from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from models.user import User
from schemas.user import UserOut
from service.auth_service import get_authenticated_user_data

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_class=JSONResponse)
async def get_user(user: Annotated[User, Depends(get_authenticated_user_data)]):
    # return user
    age_range = get_age_range(user.date_of_birth)
    anony_email = anonymize_email(user.email)
    return UserOut(
        id=str(user.id),
        first_name=user.first_name,
        email=anony_email,
        gender=user.gender,
        postcode=user.postcode,
        identity_level=user.identity_level,
        age_range=age_range,
    )


def get_age_range(date_of_birth: datetime) -> str:
    today = datetime.now()
    age = (
        today.year
        - date_of_birth.year
        - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    )
    age_ranges = {
        (20, 30): "20-30",
        (30, 40): "30-40",
        (40, 50): "40-50",
        (50, 60): "50-60",
        (60, 70): "60-70",
        (70, 80): "70-80",
        (80, 90): "80-90",
        (90, 100): "90-100",
    }
    for age_range, range_str in age_ranges.items():
        if age_range[0] <= age < age_range[1]:
            return range_str

    return "over 100"


def anonymize_email(email):
    visible_chars = 3
    if not email or len(email) <= visible_chars:
        return email

    local_part, domain_part = email.split("@", 1)
    return f"{local_part[:visible_chars]}...@{domain_part}"
