from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/unsubscribe", tags=["Unsubscribe"])


@router.get("/", response_class=HTMLResponse)
async def unsubscribe_page(request: Request):
    return templates.TemplateResponse("unsubscribe.html", {"request": request})
