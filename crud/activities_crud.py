from fastapi import HTTPException
from db.session import get_db_context_session
from models.activity import Activity
from schemas.activity import UserActivityRequestSchema
from utils.base_config import logger


def create_activity(activity_payload: UserActivityRequestSchema, user_id: str) -> Activity:
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

    with get_db_context_session() as db:
        try:
            db.add(activity)
            db.commit()
            db.refresh(activity)
        except Exception as e:
            db.rollback()
            logger.error("Error while adding activity: ", str(e))
            raise HTTPException(status_code=500, detail="something went wrong")

    return activity


def create_bulk_activities(activities: list[UserActivityRequestSchema], user_id: str) -> None:
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

    with get_db_context_session() as db:
        try:
            db.bulk_save_objects(activities_list)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Error while adding bulk activities: ", str(e))
            raise HTTPException(status_code=500, detail="something went wrong")

    return None


def get_activities_by_filters(user_id, filters) -> [list[Activity]]:
    with get_db_context_session() as db:
        query = db.query(Activity).filter_by(user_id=user_id)

        if "date" in filters:
            query = query.filter(Activity.date == filters["date"])
        if "start_date" in filters:
            query = query.filter(Activity.date >= filters["start_date"])
        if "end_date" in filters:
            query = query.filter(Activity.date <= filters["end_date"])

        return query.all()
