import json
import boto3
from utils.base_config import config as settings, logger

sns = boto3.client(
    'sns',
    region_name=settings.aws_region,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key
)


def send_message_to_sns_topic(record) -> None:
    """
    Publish message to target SNS topic.

    :param record: Data to be sent to the SNS topic.

    return None
    """
    try:
        response = sns.publish(
            TopicArn=settings.aws_sns_activity_topic_arn,
            Message=json.dumps(record),
            Subject="activity-daily-data"
        )

        logger.info(f"Message published to SNS topic => response: {response}")

    except Exception as e:
        logger.error(f"Error occurred while publishing message to SNS topic: {e}")
