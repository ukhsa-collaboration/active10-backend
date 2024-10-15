from schemas.migrations_schema import ActivitiesMigrationsRequestSchema
from service.aws_sns_service import send_message_to_sns_topic
from service.aws_sqs_service import send_message_to_sqs_queue
from utils.base_config import config as settings


async def load_bulk_activities_data(data: ActivitiesMigrationsRequestSchema, user_id: str) -> None:
    """
    Load bulk activities data to SQS queue.

    :param data: migration data from request payload
    :param user_id: user id

    :return: None
    """
    activities_migration_payload = data.model_dump()
    activities_migration_payload['user_id'] = str(user_id)
    target_sqs_url = settings.aws_sqs_activities_migrations_queue_url

    send_message_to_sqs_queue(sqs_target_url=target_sqs_url, record=activities_migration_payload)


async def publish_bulk_activities_data_to_sns(data: ActivitiesMigrationsRequestSchema, user_id: str) -> None:
    """
    Publish bulk activities data to AWS SNS topic.

    :param data: migration data from request payload
    :param user_id: user id

    :return: None
    """
    activities_migration_payload = data.model_dump()
    activities_migration_payload['user_id'] = str(user_id)
    target_sns_topic_arn = settings.aws_sns_activities_migration_topic_arn

    send_message_to_sns_topic(topic=target_sns_topic_arn, record=activities_migration_payload)
