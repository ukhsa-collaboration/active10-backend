from datetime import timezone, datetime
from fastapi import Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from db.session import get_db_session
from models.motivation import UserMotivation
from schemas.motivation import CreateUpdateUserMotivationRequest


class UserMotivationCRUD:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:
        self.db = db

    def get_by_id(self, motivation_id: UUID) -> Optional[UserMotivation]:
        return self.db.query(UserMotivation).filter_by(id=motivation_id).first()

    def get_all_by_user(self, user_id: UUID) -> List[UserMotivation]:
        return (
            self.db.query(UserMotivation)
            .filter(UserMotivation.user_id == user_id)
            .order_by(UserMotivation.created_at.desc())
            .all()
        )

    def create_motivation(self, user_id: UUID, payload: CreateUpdateUserMotivationRequest) -> UserMotivation:
        new_motivation = UserMotivation(
            user_id=user_id,
            created_at=int(datetime.now(timezone.utc).timestamp()),
            updated_at=int(datetime.now(timezone.utc).timestamp()),
            goals=[goal.model_dump() for goal in payload.goals]
        )
        self.db.add(new_motivation)
        self.db.commit()
        self.db.refresh(new_motivation)
        return new_motivation

    def update_motivation(self, motivation: UserMotivation,
                          payload: CreateUpdateUserMotivationRequest) -> UserMotivation:
        motivation.updated_at = int(datetime.now(timezone.utc).timestamp())
        motivation.goals = [goal.model_dump() for goal in payload.goals]
        self.db.commit()
        self.db.refresh(motivation)
        return motivation

    def delete_motivation(self, motivation: UserMotivation) -> None:
        self.db.delete(motivation)
        self.db.commit()
