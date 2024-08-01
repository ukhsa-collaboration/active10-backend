from datetime import datetime

from crud.activity_crud import ActivityCrud
from schemas.activity import Activity
from models.activity import Activity as ActivityModel
from fastapi import Depends


class ActivityService:
    def __init__(self, activity_crud: ActivityCrud = Depends()) -> None:
        self.activity_crud = activity_crud

    def save_activity(self, activity: Activity) -> None:
        user_activity = ActivityModel(
            mins_brisk=activity.mins_brisk,
            mins_walking=activity.mins_walking,
            steps=activity.steps,
            activity_date=datetime.fromtimestamp(activity.date).date(),
            user_id=activity.user_id,
        )
        self.activity_crud.create_activity(user_activity)
