from sendgrid import EventWebhook

from utils.base_config import config

SENDGRID_WEBHOOK_PUBLIC_KEY = config.sendgrid_webhook_public_key

def is_valid_webhook_signature(payload: str, signature: str, timestamp: str) -> bool:
    ew = EventWebhook()
    key = ew.convert_public_key_to_ecdsa(SENDGRID_WEBHOOK_PUBLIC_KEY)
    is_valid = ew.verify_signature(payload, signature, timestamp, key)

    return is_valid
