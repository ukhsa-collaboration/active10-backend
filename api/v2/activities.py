from typing import Annotated

from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from auth.auth_bearer import get_authenticated_user_data
from models import User
from schemas.activity import UserActivityRequestSchema
from service.activity_service import load_activities_data_in_sns

router = APIRouter(prefix="/activities", tags=["activities"])


@router.post("/", status_code=201, response_class=JSONResponse)
async def save_activity(
    background_task: BackgroundTasks,
    activity_payload: UserActivityRequestSchema,
    user: Annotated[User, Depends(get_authenticated_user_data)],
):
    background_task.add_task(
        load_activities_data_in_sns, activity_payload, str(user.id)
    )
    return {"message": "Success"}
