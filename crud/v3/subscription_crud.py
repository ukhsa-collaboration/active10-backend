from uuid import UUID

from fastapi import Depends, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from models import EmailPreference
from utils.custom_exceptions import CustomHTTPException, ErrorCode


def _invalid_request(message: str) -> CustomHTTPException:
    return CustomHTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code=ErrorCode.INVALID_REQUEST,
        error_message=message,
    )


class SubscriptionCRUD:
    """Email preference changes for the v3 API, with coded errors. Same rules as v1."""

    def __init__(self, db: Session = Depends(get_db_session)) -> None:  # noqa: B008
        self.db = db

    def subscribe_email_preferences(self, user_id: UUID, name: str) -> None:
        email_preference = (
            self.db.query(EmailPreference).filter_by(user_id=user_id, name=name).first()
        )
        if email_preference and email_preference.is_active:
            raise _invalid_request(
                f"User is already subscribed to email preferences with the name '{name}'"
            )

        if email_preference:
            email_preference.is_active = True
        else:
            self.db.add(EmailPreference(user_id=user_id, name=name))
        self.db.commit()

    def unsubscribe_email_preferences(self, user_id: UUID, name: str) -> None:
        email_preference = (
            self.db.query(EmailPreference).filter_by(user_id=user_id, name=name).first()
        )
        if not email_preference:
            raise _invalid_request(
                f"User is not subscribed to email preferences with the name '{name}'"
            )
        if not email_preference.is_active:
            raise _invalid_request(
                f"User is already unsubscribed from email preferences with the name '{name}'"
            )

        email_preference.is_active = False
        self.db.commit()
