from typing import Union

from fastapi import Depends
from sqlalchemy.orm import Session

from db.session import get_db_session
from models.daily_target import UserDailyTarget
from schemas.daily_target import DailyTargetRequestSchema


class UserDailyTargetCRUD:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:
        self.db = db

    def create_daily_target(self, daily_target) -> UserDailyTarget:
        self.db.add(daily_target)
        self.db.commit()
        self.db.refresh(daily_target)

        return daily_target

    def get_daily_target_by_user_id(self, uuid: str) -> Union[UserDailyTarget, None]:
        return self.db.query(UserDailyTarget).filter(UserDailyTarget.user_id == uuid).first()

    def update_daily_target(self, daily_target: UserDailyTarget, payload: DailyTargetRequestSchema) -> UserDailyTarget:
        daily_target.daily_target = payload.daily_target
        self.db.commit()
        self.db.refresh(daily_target)

        return daily_target

    def delete_daily_target(self, daily_target: UserDailyTarget) -> None:
        self.db.delete(daily_target)
        self.db.commit()
