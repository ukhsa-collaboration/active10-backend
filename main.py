from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from api.healthcheck import router as healthcheck
from api.nhs_login import router as nhs_login
from api.oauth import router as oauth
from api.unsubscribe import router as unsubscribe
from api.v1 import router as api_v1
from api.v2 import router as api_v2
from utils.base_config import config

APP_VERSION = config.app_version
APP_CODE_COMMIT_HASH = config.app_code_commit_hash

app = FastAPI(
    title="Active 10 NHS Login Backend Service",
    description=("Backend NHS Login service for Active 10 application.\n\n"),
    version=APP_VERSION,
)

CSP_POLICY = "; ".join(
    [
        "default-src 'self'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "img-src 'self' data: https://fastapi.tiangolo.com",
        "font-src 'self'",
        "connect-src 'self'",
    ]
)
HSTS_HEADER = "max-age=63072000; includeSubDomains; preload"


@app.middleware("http")
async def apply_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = HSTS_HEADER
    response.headers["Content-Security-Policy"] = CSP_POLICY
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@lru_cache
def get_config():
    return config()


# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(api_v1.router)
app.include_router(api_v2.router)
app.include_router(nhs_login)
app.include_router(oauth)
app.include_router(healthcheck)
app.include_router(unsubscribe)
