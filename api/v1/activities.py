from fastapi import APIRouter, Depends
from service.activity_service import ActivityService

from schemas.activity import Activity

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post("/", status_code=201)
async def save_activity(activity: Activity, service: ActivityService = Depends(ActivityService)):
    service.save_activity(activity)
    return activity


@router.get("/{user_id)")
async def get_activities():
    pass
