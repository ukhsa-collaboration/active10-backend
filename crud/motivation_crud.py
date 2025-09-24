from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from db.session import get_db_session
from models.motivation import UserMotivation
from schemas.motivation import CreateUpdateUserMotivationRequest


class UserMotivationCRUD:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:  # noqa: B008
        self.db = db

    def get_by_id(self, motivation_id: UUID) -> UserMotivation | None:
        return self.db.query(UserMotivation).filter_by(id=motivation_id).first()

    def get_all_by_user(self, user_id: UUID) -> list[UserMotivation]:
        return (
            self.db.query(UserMotivation)
            .filter(UserMotivation.user_id == user_id)
            .order_by(UserMotivation.created_at.desc())
            .all()
        )

    def create_motivation(
        self, user_id: UUID, payload: CreateUpdateUserMotivationRequest
    ) -> UserMotivation:
        new_motivation = UserMotivation(
            user_id=user_id,
            created_at=int(datetime.now(timezone.utc).timestamp()),  # noqa: UP017 Not supported in Python 3.10
            updated_at=int(datetime.now(timezone.utc).timestamp()),  # noqa: UP017 Not supported in Python 3.10
            goals=[goal.model_dump() for goal in payload.goals],
        )
        self.db.add(new_motivation)
        self.db.commit()
        self.db.refresh(new_motivation)
        return new_motivation

    def update_motivation(
        self, motivation: UserMotivation, payload: CreateUpdateUserMotivationRequest
    ) -> UserMotivation:
        motivation.updated_at = int(datetime.now(timezone.utc).timestamp())  # noqa: UP017 Not supported in Python 3.10
        motivation.goals = [goal.model_dump() for goal in payload.goals]
        self.db.commit()
        self.db.refresh(motivation)
        return motivation

    def delete_motivation(self, motivation: UserMotivation) -> None:
        self.db.delete(motivation)
        self.db.commit()
