from functools import lru_cache

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.healthcheck import router as healthcheck
from api.nhs_login import router as nhs_login
from api.unsubscribe import router as unsubscribe
from api.v1 import router as api_v1
from api.v2 import router as api_v2
from utils.base_config import config

app = FastAPI(
    title="Active10 Backend Service",
    description="Backend service for Active10 applications",
    version="0.1.0",
)


@lru_cache
def get_config():
    return config()


# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(api_v1.router)
app.include_router(api_v2.router)
app.include_router(nhs_login)
app.include_router(healthcheck)
app.include_router(unsubscribe)
