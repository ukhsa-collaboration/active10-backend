from models.activity_level import UserActivityLevel
from db.session import get_db_context_session
from uuid import UUID
from datetime import datetime


def get_user_activity_level(uuid: str) -> UserActivityLevel:
    with get_db_context_session() as db:
        return db.query(UserActivityLevel).filter(UserActivityLevel.user_id == uuid).order_by(UserActivityLevel.date.desc()).first()

def get_user_activity_level_by_id(user_id: str, activity_level_id: str) -> UserActivityLevel:
    with get_db_context_session() as db:
        return db.query(UserActivityLevel).filter(UserActivityLevel.user_id == user_id, UserActivityLevel.id == activity_level_id ).first()

def get_all_user_activity_levels(uuid: str) -> list[UserActivityLevel]:
    with get_db_context_session() as db:
        return db.query(UserActivityLevel).filter(UserActivityLevel.user_id == uuid).order_by(UserActivityLevel.date.desc()).all()

def create_user_activity_level(user_activity_level: UserActivityLevel) -> UserActivityLevel:
    with get_db_context_session() as db:
        current_timestamp = int(datetime.now().timestamp())
        user_activity_level.created_at = current_timestamp
        user_activity_level.updated_at = current_timestamp
        db.add(user_activity_level)
        db.commit()
        db.refresh(user_activity_level)
        return user_activity_level


def update_user_activity_level(activity_level_id: UUID, user_activity_level: UserActivityLevel) -> UserActivityLevel:
    with get_db_context_session() as db:
        existing_activity_level = db.query(UserActivityLevel).filter(UserActivityLevel.id == activity_level_id).first()
        if existing_activity_level:
            existing_activity_level.date = user_activity_level.date
            existing_activity_level.level = user_activity_level.level
            existing_activity_level.updated_at = int(datetime.now().timestamp())
            db.commit()
            db.refresh(existing_activity_level)
            return existing_activity_level
        return None