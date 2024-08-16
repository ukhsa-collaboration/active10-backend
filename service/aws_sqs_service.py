import json
import boto3
from utils.base_config import config as settings, logger

sqs = boto3.client(
    'sqs',
    region_name=settings.aws_region,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key
)


def send_message_to_sqs_queue(sqs_target_url, record) -> None:
    """
    Send message to target SQS queue.

    :param record: Data to be sent to the SQS queue.
    :param sqs_target_url: SQS queue URL.

    return None
    """
    try:
        response = sqs.send_message(
            QueueUrl=sqs_target_url,
            MessageBody=json.dumps(record),
            MessageGroupId='Active10-Data',
        )

        logger.info(f"Message sent to SQS queue: {sqs_target_url} => response: {response}")

    except Exception as e:
        logger.error(f"Error occurred while sending message to SQS queue: {e}")
