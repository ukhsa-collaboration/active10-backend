from fastapi import APIRouter
from api.v1 import users, walking_plans, activities
from api import nhs_login, healthcheck

router = APIRouter(prefix="/v1")
router.include_router(users.router)
router.include_router(walking_plans.router)
router.include_router(activities.router)