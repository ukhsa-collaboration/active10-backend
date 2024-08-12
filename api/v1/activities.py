from typing import Annotated
from fastapi import APIRouter, Depends, BackgroundTasks
from models import User
from service.activity_service import load_activity_data

from schemas.activity import UserActivityRequestSchema
from service.auth_service import get_authenticated_user_data

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post("/", status_code=201)
async def save_activity(
        background_task: BackgroundTasks,
        activity: UserActivityRequestSchema,
        user: Annotated[User, Depends(get_authenticated_user_data)]
):
    background_task.add_task(load_activity_data, activity, user)

    return {"message": "Success"}


@router.get("/{user_id)")
async def get_activities():
    pass
