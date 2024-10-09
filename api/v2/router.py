from fastapi import APIRouter
from api.v2 import activities


router = APIRouter(prefix="/v2")
router.include_router(activities.router)
