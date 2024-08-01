from sqlalchemy.orm import Session
from fastapi import Depends
from db.session import get_db_session
from models.activity import Activity


class ActivityCrud:
    def __init__(self, db: Session = Depends(get_db_session)) -> None:
        self.db = db

    def create_activity(self, activity: Activity) -> Activity:
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity
