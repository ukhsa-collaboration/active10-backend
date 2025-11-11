from functools import lru_cache

from fastapi import FastAPI, Request
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

CSP_POLICY = "; ".join(
    [
        "default-src 'self'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
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
app.include_router(healthcheck)
app.include_router(unsubscribe)
