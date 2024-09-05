from datetime import datetime

from models.user import User
from schemas.user import UserResponse, EmailPreferenceResponse


class UserService:
    def __init__(self):
        pass

    def get_user_profile(self, user: User) -> UserResponse:
        age_range = self.__get_age_range(user.date_of_birth)
        anony_email = self.__anonymize_email(user.email)
        age = self.calculate_age(user.date_of_birth)

        return UserResponse(
            id=user.id,
            first_name=user.first_name,
            email=anony_email,
            gender=user.gender,
            postcode=user.postcode,
            identity_level=user.identity_level,
            age_range=age_range,
            age=age,
            email_preferences=[EmailPreferenceResponse(
                id=ep.id,
                name=ep.name,
                is_active=ep.is_active,
            ) for ep in user.email_preferences if user.email_preferences],
        )

    def __get_age_range(self, date_of_birth: datetime) -> str:
        today = datetime.now()
        age = (
            today.year
            - date_of_birth.year
            - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        )

        age_ranges = {
            (18, 24): "18 to 24",
            (25, 34): "25 to 34",
            (35, 44): "35 to 44",
            (45, 54): "45 to 54",
            (55, 64): "55 to 64",
        }
        for age_range in age_ranges:
            if age_range[0] <= age <= age_range[1]:
                return age_ranges[age_range]
        if age >= 65:
            return "65 or over"
        return "Out of range"

    def __anonymize_email(self, email: str):
        visible_chars = 3
        if not email or len(email) <= visible_chars:
            return email

        local_part, domain_part = email.split("@", 1)
        return f"{local_part[:visible_chars]}...@{domain_part}"

    def calculate_age(self, date_of_birth):
        today = datetime.today()

        age = today.year - date_of_birth.year

        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1

        return age
