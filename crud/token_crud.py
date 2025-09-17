from fastapi import Depends
from future.backports.datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.session import get_db_session
from models.user import UserToken
from utils.base_config import logger


class TokenCRUD:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:  # noqa: B008
        self.db = db

    def create_or_update_user_token(self, user_id: str, token: str) -> UserToken | None:
        try:
            user_token = self.db.query(UserToken).filter(UserToken.user_id == user_id).first()

            if user_token:
                user_token.token = token
                user_token.created_at = datetime.utcnow()
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

    def get_token_by_user_id(self, user_id: str) -> UserToken | None:
        return self.db.query(UserToken).filter(UserToken.user_id == user_id).first()

    def validate_user_token(self, user_id: str, token: str) -> UserToken | None:
        return (
            self.db.query(UserToken)
            .filter(UserToken.user_id == user_id, UserToken.token == token)
            .first()
        )
