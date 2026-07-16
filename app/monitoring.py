"""
Azure Application Insights monitoring setup.

Tracks:
- Background job execution (send_reservation_reminders)
- Email delivery success/failure
- Custom metrics and events
"""

import logging
import os
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TraceProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

logger = logging.getLogger(__name__)


def setup_application_insights():
    """Initialize Azure Application Insights monitoring."""
    connection_string = os.getenv("APPINSIGHTS_CONNECTION_STRING")

    if not connection_string:
        logger.warning("⚠️  APPINSIGHTS_CONNECTION_STRING not set, monitoring disabled")
        return False

    try:
        configure_azure_monitor(connection_string=connection_string)
        logger.info("✅ Application Insights initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Error initializing Application Insights: {e}")
        return False


def track_scheduler_job(job_name: str, status: str, details: dict = None):
    """
    Track scheduler job execution.

    Args:
        job_name: Name of the job (e.g., "send_reservation_reminders")
        status: "success" or "failure"
        details: Additional details (email count, errors, etc.)
    """
    tracer = trace.get_tracer(__name__)

    attributes = {
        "job.name": job_name,
        "job.status": status,
    }

    if details:
        for key, value in details.items():
            attributes[f"job.{key}"] = value

    with tracer.start_as_current_span(f"scheduler.{job_name}") as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)

        logger.info(f"📊 Scheduler event tracked: {job_name} - {status}", extra=attributes)


def track_email_sent(recipient: str, subject: str, success: bool, message_id: str = None, error: str = None):
    """
    Track email delivery.

    Args:
        recipient: Email recipient
        subject: Email subject
        success: True if sent successfully
        message_id: Azure Communication Services message ID
        error: Error message if failed
    """
    tracer = trace.get_tracer(__name__)

    attributes = {
        "email.recipient": recipient,
        "email.subject": subject,
        "email.success": success,
    }

    if message_id:
        attributes["email.message_id"] = message_id
    if error:
        attributes["email.error"] = error

    span_name = "email.sent_success" if success else "email.sent_failure"

    with tracer.start_as_current_span(span_name) as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)

        status = "✅" if success else "❌"
        logger.info(f"{status} Email tracked: {recipient} - {subject}", extra=attributes)


def track_custom_metric(metric_name: str, value: float, dimensions: dict = None):
    """
    Track custom metric.

    Args:
        metric_name: Name of the metric
        value: Numeric value
        dimensions: Additional dimensions
    """
    meter = metrics.get_meter(__name__)
    counter = meter.create_counter(metric_name)

    attributes = dimensions or {}
    counter.add(value, attributes)

    logger.debug(f"📈 Metric tracked: {metric_name}={value}", extra={"dimensions": attributes})
