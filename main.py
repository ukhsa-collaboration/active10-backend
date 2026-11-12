from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi_cprofile.profiler import CProfileMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from api.healthcheck import router as healthcheck
from api.nhs_login import router as nhs_login
from api.unsubscribe import router as unsubscribe
from api.v1 import router as api_v1
from api.v2 import router as api_v2
from api.v3 import router as api_v3
from service.open_telemetry_service import setup_telemetry
from utils.base_config import config
from utils.custom_exceptions import CustomHTTPException, custom_http_exception_handler

setup_telemetry()

APP_VERSION = config.app_version
APP_CODE_COMMIT_HASH = config.app_code_commit_hash


app = FastAPI(
    title="Active 10 NHS Login Backend Service",
    description=("Backend NHS Login service for Active 10 application.\n\n"),
    version=APP_VERSION,
)

app.add_middleware(
    CProfileMiddleware,
    enable=config.cprofile_enable,
    print_each_request=True,
    strip_dirs=False,
    sort_by="cumulative",
)


def _drop_query_string(span, scope):
    if span is None or not span.is_recording():
        return

    path = scope.get("path", "")
    span.set_attribute("http.target", path)
    span.set_attribute("http.url", path)
    span.set_attribute("url.full", path)
    span.set_attribute("url.query", "REDACTED")


FastAPIInstrumentor.instrument_app(
    app,
    excluded_urls="healthcheck",
    server_request_hook=_drop_query_string,
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
NO_CACHE_PATHS = {
    "/nhs_login/callback",
    "/nhs_login/logout",
    "/nhs_login/disconnect",
    "/v3/users/sync",
    "/v3/auth/logout",
    "/v3/auth/disconnect",
}


@app.middleware("http")
async def apply_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = HSTS_HEADER
    response.headers["Content-Security-Policy"] = CSP_POLICY
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    if request.url.path in NO_CACHE_PATHS:
        response.headers["Cache-Control"] = "no-cache"
    return response


app.add_exception_handler(CustomHTTPException, custom_http_exception_handler)


@lru_cache
def get_config():
    return config()


# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(api_v1.router)
app.include_router(api_v2.router)
app.include_router(api_v3.router)
app.include_router(nhs_login)
app.include_router(healthcheck)
app.include_router(unsubscribe)
