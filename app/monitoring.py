"""
Azure Application Insights monitoring setup.

Tracks:
- Background job execution (send_reservation_reminders)
- Email delivery success/failure
- Custom metrics and events
"""

import logging
import os

logger = logging.getLogger(__name__)

_initialized = False


def setup_application_insights():
    """Initialize Azure Application Insights monitoring."""
    global _initialized

    connection_string = os.getenv("APPINSIGHTS_CONNECTION_STRING")

    if not connection_string:
        logger.debug("Application Insights connection string not set — monitoring disabled")
        return False

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=connection_string)
        _initialized = True
        logger.info("✅ Application Insights initialized")
        return True
    except ImportError:
        logger.warning("Azure Monitor OpenTelemetry not installed — monitoring unavailable")
        return False
    except Exception as e:
        logger.warning(f"Failed to initialize Application Insights: {e}")
        return False


def track_scheduler_job(job_name: str, status: str, details: dict = None):
    """Track scheduler job execution."""
    if not _initialized:
        return

    try:
        from opentelemetry import trace

        tracer = trace.get_tracer(__name__)
        attributes = {"job.name": job_name, "job.status": status}

        if details:
            for key, value in details.items():
                attributes[f"job.{key}"] = value

        with tracer.start_as_current_span(f"scheduler.{job_name}") as span:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        logger.debug(f"Scheduler event tracked: {job_name} - {status}")
    except Exception as e:
        logger.debug(f"Failed to track scheduler job: {e}")


def track_email_sent(recipient: str, subject: str, success: bool, message_id: str = None, error: str = None):
    """Track email delivery."""
    if not _initialized:
        return

    try:
        from opentelemetry import trace

        tracer = trace.get_tracer(__name__)
        attributes = {"email.recipient": recipient, "email.subject": subject, "email.success": success}

        if message_id:
            attributes["email.message_id"] = message_id
        if error:
            attributes["email.error"] = error

        span_name = "email.sent_success" if success else "email.sent_failure"

        with tracer.start_as_current_span(span_name) as span:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        logger.debug(f"Email tracked: {recipient} - {subject}")
    except Exception as e:
        logger.debug(f"Failed to track email: {e}")
