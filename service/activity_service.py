from schemas.activity import UserActivityRequestSchema
from service.aws_sqs_service import send_message_to_sqs_queue


async def load_activity_data(activity: UserActivityRequestSchema, user) -> None:
    activity_payload = activity.model_dump()
    activity_payload['user_id'] = str(user.id)
    send_message_to_sqs_queue(activity_payload)
