from fastapi import FastAPI
from functools import lru_cache

from api.v1 import router as api_v1
from api.nhs_login import router as nhs_login
from api.healthcheck import router as healthcheck
from utils.base_config import config


app = FastAPI(
    title="Active10 Backend Service",
    description="Backend service for Active10 applications",
    version="0.1.0",
)

@lru_cache
def get_config():
    return config()


app.include_router(api_v1.router)
app.include_router(nhs_login)
app.include_router(healthcheck)
