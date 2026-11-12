from datetime import datetime, timezone
from typing import Any

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError

from crud.user_crud import UserCRUD
from models.user import DeleteAudit, User, UserToken
from utils.base_config import logger
from utils.custom_exceptions import CustomHTTPException, ErrorCode


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # noqa: UP017 Not supported in Python 3.10


class KeycloakUserCRUD(UserCRUD):
    """User lookups for the v3 API, kept apart so the legacy UserCRUD stays unchanged."""

    def get_user_by_keycloak_sub(self, keycloak_sub: str) -> User | None:
        return self.db.query(User).filter(User.keycloak_sub == keycloak_sub).first()

    def get_users_by_nhs_number(self, nhs_number: str) -> list[User]:
        return self.db.query(User).filter(User.nhs_number == nhs_number).all()

    def get_legacy_tokens(self, user_id) -> list[UserToken]:
        return self.db.query(UserToken).filter(UserToken.user_id == user_id).all()

    def save_synced_user(
        self, user: User, profile: dict[str, Any], legacy_tokens: list[UserToken]
    ) -> User:
        """
        Applies the synced profile and removes the user's legacy tokens in one commit. The
        changes are made inside a savepoint, so an IntegrityError rolls back only the savepoint
        and leaves the session usable for a retry.
        """
        with self.db.begin_nested():
            for field, value in profile.items():
                setattr(user, field, value)
            self.db.add(user)
            for legacy_token in legacy_tokens:
                self.db.delete(legacy_token)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_status(self, user: User, status_value: str) -> None:
        user.status = status_value
        user.status_updated_at = _utc_now()
        self.db.commit()

    def delete_user_with_audit(self, user: User, reason: str) -> None:
        """
        Deletes the user, and through the database cascades all their data, with a
        DeleteAudit row in the same commit. deleted_at is set here because the model's default
        is evaluated once, at import.
        """
        user_id = user.id
        try:
            with self.db.begin_nested():
                self.db.delete(user)
                self.db.add(DeleteAudit(user_id=user_id, delete_reason=reason))
            self.db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete user {user_id}: {type(e).__name__}")
            raise CustomHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code=ErrorCode.INTERNAL_ERROR,
                error_message="Failed to delete user",
            ) from e
