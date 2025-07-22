from app.api.v1 import user
from fastapi.routing import APIRouter

routes = APIRouter(prefix="/v1")

routes.include_router(user.router)
