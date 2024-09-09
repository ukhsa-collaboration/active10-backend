from models import User
from schemas.migrations_schema import ActivitiesMigrationsRequestSchema
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
