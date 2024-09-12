from sqlalchemy.orm import Session
from fastapi import Depends
from db.session import get_db_session
from models.activity import Activity
from schemas.activity import UserActivityRequestSchema


class ActivityCrud:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:
        self.db = db

    def create_activity(self, activity_payload: UserActivityRequestSchema, user_id: str) -> Activity:
        activity = Activity(
            date=activity_payload.date,
            rewards=activity_payload.rewards,
            user_postcode=activity_payload.user_postcode,
            user_age_range=activity_payload.user_age_range,
            brisk_minutes=activity_payload.activity.brisk_minutes,
            walking_minutes=activity_payload.activity.walking_minutes,
            steps=activity_payload.activity.steps,
            user_id=user_id
        )
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)

        return activity

    def create_bulk_activities(self, activities: list[UserActivityRequestSchema], user_id: str) -> None:
        activities_list = []

        for activity_payload in activities:
            activity = Activity(
                date=activity_payload.date,
                rewards=activity_payload.rewards,
                user_postcode=activity_payload.user_postcode,
                user_age_range=activity_payload.user_age_range,
                brisk_minutes=activity_payload.activity.brisk_minutes,
                walking_minutes=activity_payload.activity.walking_minutes,
                steps=activity_payload.activity.steps,
                user_id=user_id
            )
            activities_list.append(activity)

        self.db.bulk_save_objects(activities_list)
        self.db.commit()
        return None

    def get_activities_by_filters(self, user_id, filters) -> [list[Activity]]:
        query = self.db.query(Activity).filter_by(user_id=user_id)

        if "date" in filters:
            query = query.filter(Activity.date == filters["date"])
        if "start_date" in filters:
            query = query.filter(Activity.date >= filters["start_date"])
        if "end_date" in filters:
            query = query.filter(Activity.date <= filters["end_date"])

        return query.all()
