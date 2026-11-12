from enum import Enum

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    """Machine readable error codes returned by the v3 API alongside the error message."""

    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    ACCOUNT_CONFLICT = "ACCOUNT_CONFLICT"
    NHS_NUMBER_MISSING = "NHS_NUMBER_MISSING"
    UPSTREAM_PROFILE_INCOMPLETE = "UPSTREAM_PROFILE_INCOMPLETE"
    REFRESH_TOKEN_INVALID = "REFRESH_TOKEN_INVALID"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"


class CustomHTTPException(HTTPException):
    """HTTP exception carrying an error code. Raised only by v3 code."""

    def __init__(self, status_code: int, error_code: ErrorCode, error_message: str) -> None:
        super().__init__(status_code=status_code, detail=error_message)
        self.error_code = error_code
        self.error_message = error_message


def custom_http_exception_handler(_: Request, exc: CustomHTTPException) -> JSONResponse:
    """
    Handler for CustomHTTPException only, so legacy errors keep FastAPI's default response.
    """
    headers = (
        {"WWW-Authenticate": "Bearer"} if exc.status_code == status.HTTP_401_UNAUTHORIZED else None
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.error_message,
            "error": {"code": exc.error_code.value, "message": exc.error_message},
        },
        headers=headers,
    )
