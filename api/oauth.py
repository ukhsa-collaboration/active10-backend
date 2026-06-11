from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query
from fastapi.responses import RedirectResponse
from starlette.responses import JSONResponse

from service.nhs_login_service import NHSLoginService

router = APIRouter(tags=["OAuth"])


@router.get("/authorize", response_class=RedirectResponse, status_code=307)
async def authorize(  # noqa: PLR0913 - Lots of parameters but are needed for readability and to match the OAuth2 specification
    service: Annotated[NHSLoginService, Depends()],
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query("S256"),
    state: str | None = Query(None),
    scope: str | None = Query(None),
):
    url = service.start_authorization(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        client_state=state,
        scope=scope,
    )
    return RedirectResponse(url)


@router.post("/token", response_class=JSONResponse, status_code=200)
async def token(  # noqa: PLR0913 - Lots of parameters but they are needed for readability and to match the OAuth2 specification
    service: Annotated[NHSLoginService, Depends()],
    grant_type: str = Form(...),
    code: str = Form(...),
    code_verifier: str = Form(...),
    redirect_uri: str | None = Form(None),
    client_id: str | None = Form(None),
):
    if grant_type != "authorization_code":
        return JSONResponse(status_code=400, content={"detail": "Unsupported grant_type"})

    data = service.exchange_code_for_token(
        code=code,
        code_verifier=code_verifier,
        client_id=client_id,
        redirect_uri=redirect_uri,
    )
    return data
