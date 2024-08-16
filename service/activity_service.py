from schemas.activity import UserActivityRequestSchema
from service.aws_sqs_service import send_message_to_sqs_queue
from utils.base_config import config as settings


async def load_activity_data(activity: UserActivityRequestSchema, user) -> None:
    activity_payload = activity.model_dump()
    activity_payload['user_id'] = str(user.id)
    target_sqs_url = settings.aws_sqs_queue_url

    send_message_to_sqs_queue(sqs_target_url=target_sqs_url, record=activity_payload)
