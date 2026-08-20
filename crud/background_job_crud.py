from uuid import UUID

from db.session import get_db_context_session
from models.background_job import BackgroundJob
from utils.base_config import logger


def create_background_job(user_id: UUID, status: str) -> BackgroundJob:
    with get_db_context_session() as db:
        try:
            background_job = BackgroundJob(user_id=user_id, status=status)
            db.add(background_job)
            db.commit()
            db.refresh(background_job)
        except Exception as exc:
            db.rollback()
            logger.error(f"Error while creating background job: {exc}")
            raise

    return background_job


def get_background_job(job_id: UUID) -> BackgroundJob | None:
    with get_db_context_session() as db:
        return db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()


def update_background_job_status(job_id: UUID, status: str) -> bool:
    with get_db_context_session() as db:
        try:
            background_job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
            if not background_job:
                return False

            background_job.status = status
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error(f"Error while updating background job status: {exc}")
            raise

    return True
