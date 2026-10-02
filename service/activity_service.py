from schemas.activity import UserActivityRequestSchema
from service.aws_sns_service import send_message_to_sns_topic
from service.aws_sqs_service import send_message_to_sqs_queue
from service.open_telemetry_service import (
    ACTIVITIES_FLOW,
    STEP_ACTIVITY_PUBLISH,
    step_span,
)
from utils.base_config import config as settings


def load_activity_data(activity: UserActivityRequestSchema, user_id) -> None:
    activity_payload = activity.model_dump()
    activity_payload["user_id"] = str(user_id)
    target_sqs_url = settings.aws_sqs_queue_url

    send_message_to_sqs_queue(sqs_target_url=target_sqs_url, record=activity_payload)


def load_activities_data_in_sns(activity: UserActivityRequestSchema, user_id) -> None:
    activity_payload = activity.model_dump()
    activity_payload["user_id"] = str(user_id)
    target_sns_topic_arn = settings.aws_sns_activity_topic_arn

    with step_span(STEP_ACTIVITY_PUBLISH, ACTIVITIES_FLOW):
        send_message_to_sns_topic(topic=target_sns_topic_arn, record=activity_payload)
