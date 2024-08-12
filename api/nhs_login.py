from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse

from service.nhs_login_service import NHSLoginService

router = APIRouter(prefix="/nhs_login", tags=["NHS Login"])


@router.get("/{app_name}/{app_internal_id}")
async def nhs_login(app_name: str, app_internal_id: str, service: NHSLoginService = Depends()):
    url = service.get_nhs_login_url(app_name, app_internal_id)
    return RedirectResponse(url)


@router.get("/callback", response_class=RedirectResponse, status_code=301)
async def nhs_login_callback(request: Request, service: NHSLoginService = Depends()):
    req_args = dict(request.query_params)
    deep_link = service.process_callback(req_args)
    return RedirectResponse(deep_link)


@router.post("/logout")
async def nhs_logout(service: NHSLoginService = Depends()):
    pass
