from fastapi import Depends
from sqlalchemy.orm import Session

from db.session import get_db_session
from models.walking_plan import UserWalkingPlan
from schemas.walking_plan import WalkingPlanRequestSchema


class UserWalkingPlanCRUD:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:  # noqa: B008
        self.db = db

    def create_walking_plan(self, walking_plan) -> UserWalkingPlan:
        self.db.add(walking_plan)
        self.db.commit()
        self.db.refresh(walking_plan)

        return walking_plan

    def get_walking_plan_by_user_id(self, uuid: str) -> UserWalkingPlan | None:
        return self.db.query(UserWalkingPlan).filter(UserWalkingPlan.user_id == uuid).first()

    def update_walking_plan(
        self, walking_plan: UserWalkingPlan, payload: WalkingPlanRequestSchema
    ) -> UserWalkingPlan:
        walking_plan.walking_plan_data = payload.walking_plan_data
        self.db.commit()
        self.db.refresh(walking_plan)

        return walking_plan

    def delete_walking_plan(self, walking_plan: UserWalkingPlan) -> None:
        self.db.delete(walking_plan)
        self.db.commit()
