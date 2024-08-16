from typing import Union, List, Dict

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

    def get_daily_targets_by_filters(self, user_id: str, filters: Dict) -> [List[UserDailyTarget]]:
        query = self.db.query(UserDailyTarget).filter_by(user_id=user_id)

        if "date" in filters:
            query = query.filter(UserDailyTarget.date == filters["date"])
        if "start_date" in filters:
            query = query.filter(UserDailyTarget.date >= filters["start_date"])
        if "end_date" in filters:
            query = query.filter(UserDailyTarget.date <= filters["end_date"])
        if "min_daily_target" in filters:
            query = query.filter(UserDailyTarget.daily_target >= filters["min_daily_target"])
        if "max_daily_target" in filters:
            query = query.filter(UserDailyTarget.daily_target <= filters["max_daily_target"])

        return query.all()

    def get_daily_targets_by_user_id(self, uuid: str) -> [List[UserDailyTarget]]:
        return self.db.query(UserDailyTarget).filter(UserDailyTarget.user_id == uuid).all()

    def update_daily_target(self, daily_target: UserDailyTarget, payload: DailyTargetRequestSchema) -> UserDailyTarget:
        daily_target.daily_target = payload.daily_target
        daily_target.date = payload.date
        self.db.commit()
        self.db.refresh(daily_target)

        return daily_target

    def delete_daily_target(self, daily_target: UserDailyTarget) -> None:
        self.db.delete(daily_target)
        self.db.commit()

    def get_user_daily_target_by_id(self, user_id, target_id) -> Union[UserDailyTarget, None]:
        return self.db.query(UserDailyTarget).filter_by(user_id=user_id, id=target_id).first()

    def get_user_target_by_payload_data(self, user_id, data):
        return self.db.query(UserDailyTarget).filter_by(
            user_id=user_id, date=data.date, daily_target=data.daily_target
        ).first()
