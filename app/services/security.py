import logging
from sqlalchemy.orm import Session
from app import models

logger = logging.getLogger(__name__)


def log_security_event(
    db: Session,
    event_type: str,
    severity: str,
    message: str,
    user_id: str | None = None,
    username: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    context: dict | None = None,
):
    """Log security event"""
    event = models.SecurityEvent(
        event_type=event_type,
        user_id=user_id,
        username=username,
        ip_address=ip_address,
        user_agent=user_agent,
        severity=severity,
        message=message,
        context=context,
    )
    db.add(event)
    db.commit()

    if severity == "high":
        logger.warning(
            f"SECURITY ALERT [{event_type}]: {message}",
            extra={
                "event_type": event_type,
                "severity": severity,
                "user_id": str(user_id),
                "ip_address": ip_address,
            },
        )
    else:
        logger.info(
            f"Security event [{event_type}]: {message}",
            extra={
                "event_type": event_type,
                "severity": severity,
            },
        )
