from fastapi import APIRouter, Request
from fastapi.background import BackgroundTasks
from fastapi.responses import JSONResponse

from service.webhook_service import handle_sendgrid_webhook
from utils.base_config import logger
from utils.webhook_utils import is_valid_webhook_signature

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


@router.post("/sendgrid/", response_class=JSONResponse, status_code=200)
async def handle_sendgrid_events_webhook(
        request: Request,
        background_job: BackgroundTasks
):
    headers = request.headers
    webhook_signature = headers.get("x-twilio-email-event-webhook-signature")
    webhook_timestamp = headers.get("x-twilio-email-event-webhook-timestamp")
    raw_payload = await request.body()
    body = await request.json()
    webhook_type = body[0].get("webhook_type", None)

    if not webhook_signature or not webhook_timestamp:
        return JSONResponse(content={"message": "Invalid request"}, status_code=400)

    if not is_valid_webhook_signature(raw_payload.decode('utf-8'), str(webhook_signature), str(webhook_timestamp)):
        return JSONResponse(content={"message": "Invalid signature"}, status_code=400)

    if webhook_type:
        background_job.add_task(handle_sendgrid_webhook, body, webhook_type)

    else:
        logger.error(f"Missing custom args ( webhook_type ) in payload.")
        return JSONResponse(content={"message": "OK"}, status_code=200)
