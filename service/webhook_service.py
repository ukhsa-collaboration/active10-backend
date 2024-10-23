from db.session import get_db_context_session
from models import LogoutUserEmailLogs, MonthlyReportEmailLogs
from utils.base_config import logger


def insert_logout_logs(success_objects_list, failed_objects_list):
    with get_db_context_session() as db:
        for success_object in success_objects_list:
            db_object = LogoutUserEmailLogs(
                user_id=success_object.get("user_id"),
                user_email=success_object.get("email"),
                notification_type=success_object.get("notification_type"),
                email_delivery_status="Sent",
                timestamp=int(success_object.get("timestamp")),
                message_id=success_object.get("sg_message_id")
            )
            db.add(db_object)

        for failed_object in failed_objects_list:
            db_object = LogoutUserEmailLogs(
                user_id=failed_object.get("user_id"),
                user_email=failed_object.get("email"),
                notification_type=failed_object.get("notification_type"),
                email_delivery_status="Failed",
                timestamp=int(failed_object.get("timestamp")),
                failure_reason=failed_object.get("reason"),
                message_id=failed_object.get("sg_message_id")
            )
            db.add(db_object)
        db.commit()


def insert_monthly_report_logs(success_objects_list, failed_objects_list):
    with get_db_context_session() as db:
        for success_object in success_objects_list:
            db_object = MonthlyReportEmailLogs(
                report_month=success_object.get("report_month"),
                batch_id=success_object.get("batch_id"),
                user_id=success_object.get("user_id"),
                user_email=success_object.get("email"),
                email_delivery_status="Sent",
                timestamp=int(success_object.get("timestamp")),
                message_id=success_object.get("sg_message_id")
            )
            db.add(db_object)

        for failed_object in failed_objects_list:
            db_object = MonthlyReportEmailLogs(
                report_month=failed_object.get("report_month"),
                batch_id=failed_object.get("batch_id"),
                user_id=failed_object.get("user_id"),
                user_email=failed_object.get("email"),
                email_delivery_status="Failed",
                timestamp=int(failed_object.get("timestamp")),
                failure_reason=failed_object.get("reason"),
                message_id=failed_object.get("sg_message_id")
            )
            db.add(db_object)
        db.commit()


def handle_sendgrid_webhook(body, webhook_type):
    success_objects_list = []
    failed_objects_list = []

    for event in body:
        if event.get("event") == "delivered":
            success_objects_list.append(event)
        elif event.get("event") in ["bounced", "dropped"]:
            failed_objects_list.append(event)
        else:
            ...  # skipped other events ["deferred", "processed"]

    if webhook_type == "logout_user_notification":
        if success_objects_list and failed_objects_list:
            insert_logout_logs(success_objects_list, failed_objects_list)

    elif webhook_type == "monthly_report":
        if success_objects_list and failed_objects_list:
            insert_monthly_report_logs(success_objects_list, failed_objects_list)

    else:
        logger.error(f"Null or unhandled webhook type = {webhook_type}")
