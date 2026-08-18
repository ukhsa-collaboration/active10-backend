import json

import boto3
from opentelemetry.trace import Status, StatusCode

from service.open_telemetry_service import message_trace_attributes, tracer
from utils.base_config import logger

sns = boto3.client("sns")


def send_message_to_sns_topic(topic, record) -> None:
    """
    Publish message to target SNS topic.

    :param topic: Target SNS topic arn.
    :param record: Data to be sent to the SNS topic.

    return None
    """
    with tracer.start_as_current_span("sns-publish") as span:
        span.set_attribute("messaging.system", "aws_sns")
        span.set_attribute("messaging.destination", topic)
        try:
            response = sns.publish(
                TopicArn=topic,
                Message=json.dumps(record),
                Subject="activity-daily-data",
                MessageAttributes=message_trace_attributes(),
            )

            logger.info(f"Message published to SNS topic {topic} => response: {response}")

        except Exception as e:
            # the failure is swallowed here, so mark the span ourselves
            span.set_status(Status(StatusCode.ERROR, type(e).__name__))
            logger.error(f"Error occurred while publishing message to SNS topic {topic}: {e}")
