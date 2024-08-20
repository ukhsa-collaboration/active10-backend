from typing import Annotated
from fastapi import APIRouter, Depends, BackgroundTasks

from auth.auth_bearer import get_authenticated_user_data
from models import User
from service.activity_service import load_activity_data

from schemas.activity import UserActivityRequestSchema

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
