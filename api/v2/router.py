from fastapi import APIRouter

from api.v2 import activities, data_migrations

router = APIRouter(prefix="/v2")
router.include_router(activities.router)
router.include_router(data_migrations.router)
