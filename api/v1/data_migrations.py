from typing import Annotated
from fastapi import APIRouter, Depends, BackgroundTasks
from models import User
from schemas.migrations_schema import ActivitiesMigrationsRequestSchema
from service.auth_service import get_authenticated_user_data
from service.migrations_service import load_bulk_activities_data

router = APIRouter(prefix="/migrations", tags=["migrations"])


@router.post("/activities/", status_code=201)
async def save_bulk_activities(
        background_task: BackgroundTasks,
        data: ActivitiesMigrationsRequestSchema,
        user: Annotated[User, Depends(get_authenticated_user_data)]
):
    background_task.add_task(load_bulk_activities_data, data, user)

    return {"message": "Success"}
