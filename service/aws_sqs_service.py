import json

import boto3
from opentelemetry.trace import Status, StatusCode

from service.open_telemetry_service import message_trace_attributes, tracer
from utils.base_config import logger

sqs = boto3.client("sqs")


def send_message_to_sqs_queue(sqs_target_url, record) -> None:
    """
    Send message to target SQS queue.

    :param record: Data to be sent to the SQS queue.
    :param sqs_target_url: SQS queue URL.

    return None
    """
    with tracer.start_as_current_span("sqs-send") as span:
        span.set_attribute("messaging.system", "aws_sqs")
        span.set_attribute("messaging.destination", sqs_target_url)
        try:
            response = sqs.send_message(
                QueueUrl=sqs_target_url,
                MessageBody=json.dumps(record),
                MessageGroupId="Active10-Data",
                MessageAttributes=message_trace_attributes(),
            )

            logger.info(f"Message sent to SQS queue: {sqs_target_url} => response: {response}")

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, type(e).__name__))
            logger.error(f"Error occurred while sending message to SQS queue: {e}")
