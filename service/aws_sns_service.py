import json
import boto3
from utils.base_config import config as settings, logger

sns = boto3.client('sns')


def send_message_to_sns_topic(topic, record) -> None:
    """
    Publish message to target SNS topic.

    :param topic: Target SNS topic arn.
    :param record: Data to be sent to the SNS topic.

    return None
    """
    try:
        response = sns.publish(
            TopicArn=topic,
            Message=json.dumps(record),
            Subject="activity-daily-data"
        )

        logger.info(f"Message published to SNS topic {topic} => response: {response}")

    except Exception as e:
        logger.error(f"Error occurred while publishing message to SNS topic {topic}: {e}")
