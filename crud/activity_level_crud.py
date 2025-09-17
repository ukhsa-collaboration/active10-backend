from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from db.session import get_db_session
from models.activity_level import UserActivityLevel
from schemas.activity_level import ActivityLevelRequestSchema


class UserActivityLevelCRUD:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:  # noqa: B008
        self.db = db

    def get_latest_by_user(self, user_id: UUID) -> UserActivityLevel | None:
        return (
            self.db.query(UserActivityLevel)
            .filter(UserActivityLevel.user_id == user_id)
            .order_by(UserActivityLevel.created_at.desc())
            .first()
        )

    def get_by_id(self, user_id: UUID, activity_level_id: UUID) -> UserActivityLevel | None:
        return (
            self.db.query(UserActivityLevel)
            .filter(
                UserActivityLevel.user_id == user_id,
                UserActivityLevel.id == activity_level_id,
            )
            .first()
        )

    def get_all_by_user(self, user_id: UUID) -> list[UserActivityLevel]:
        return (
            self.db.query(UserActivityLevel)
            .filter(UserActivityLevel.user_id == user_id)
            .order_by(UserActivityLevel.created_at.desc())
            .all()
        )

    def create(self, user_id: UUID, payload: ActivityLevelRequestSchema) -> UserActivityLevel:
        current_timestamp = int(datetime.now(timezone.utc).timestamp())  # noqa: UP017 Not supported in Python 3.10
        new_activity_level = UserActivityLevel(
            user_id=user_id,
            level=payload.level,
            created_at=current_timestamp,
            updated_at=current_timestamp,
        )
        self.db.add(new_activity_level)
        self.db.commit()
        self.db.refresh(new_activity_level)
        return new_activity_level

    def update(
        self, activity_level: UserActivityLevel, payload: ActivityLevelRequestSchema
    ) -> UserActivityLevel | None:
        activity_level.updated_at = int(datetime.now(timezone.utc).timestamp())  # noqa: UP017 Not supported in Python 3.10
        activity_level.level = payload.level
        self.db.commit()
        self.db.refresh(activity_level)
        return activity_level

    def delete(self, activity_level: UserActivityLevel) -> None:
        self.db.delete(activity_level)
        self.db.commit()
