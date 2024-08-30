from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db_session
from models import EmailPreference


class SubscriptionCRUD:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:
        self.db = db

    def subscribe_email_preferences(self, user_id: str, name: str) -> None:
        """
        Subscribe a user to email preferences.

        Args:
            user_id (str): The user ID.
            name (str): The email preference name.

        Raises:
            HTTPException: If the user is already subscribed to email preferences with the same name.
        """
        email_preference = self.db.query(EmailPreference).filter_by(user_id=user_id, name=name).first()

        if email_preference:
            if email_preference.is_active:
                raise HTTPException(
                    status_code=400, detail=f"User is already subscribed to email preferences with the name '{name}'"
                )
            else:
                email_preference.is_active = True
                self.db.commit()
                self.db.refresh(email_preference)

        else:
            email_preference = EmailPreference(user_id=user_id, name=name)
            self.db.add(email_preference)
            self.db.commit()
            self.db.refresh(email_preference)

    def unsubscribe_email_preferences(self, user_id: str, name: str) -> None:
        """
        Unsubscribe a user from email preferences.

        Args:
            user_id (str): The user ID.
            name (str): The email preference name.

        Raises:
            HTTPException: If the user is not subscribed to email preferences.
        """
        email_preference = self.db.query(EmailPreference).filter_by(user_id=user_id, name=name).first()

        if email_preference:
            if not email_preference.is_active:
                raise HTTPException(
                    status_code=400, detail=f"User is already unsubscribed from email preferences with the name '{name}'"
                )

            email_preference.is_active = False
            self.db.commit()
            self.db.refresh(email_preference)
        else:
            raise HTTPException(
                status_code=400, detail=f"User is not subscribed to email preferences with the name '{name}'"
            )
