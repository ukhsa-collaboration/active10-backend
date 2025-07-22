from datetime import datetime, timezone
from typing import Union, Optional

from app.core.logger import logger
from app.db.session import get_db_session
from app.models import UserToken
from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class TokenCRUD:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:
        self.db = db

    def create_or_update_user_token(
        self, user_id: str, token: str
    ) -> Optional[UserToken]:
        try:
            user_token = (
                self.db.query(UserToken).filter(UserToken.user_id == user_id).first()
            )

            if user_token:
                user_token.token = token
                user_token.created_at = datetime.now(timezone.utc)
            else:
                user_token = UserToken(user_id=user_id, token=token)
                self.db.add(user_token)

            self.db.commit()
            self.db.refresh(user_token)

            return user_token
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error while creating or updating user token: {e}")
            return None

    def get_token_by_user_id(self, user_id: str) -> Union[UserToken, None]:
        return self.db.query(UserToken).filter(UserToken.user_id == user_id).first()

    def validate_user_token(self, user_id: str, token: str) -> Union[UserToken, None]:
        return (
            self.db.query(UserToken)
            .filter(UserToken.user_id == user_id, UserToken.token == token)
            .first()
        )
