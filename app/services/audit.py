import logging
from sqlalchemy.orm import Session
from app import models

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    admin_user_id: str,
    action: str,
    target_user_id: str | None = None,
    target_resource: str | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    """Log admin action to audit trail"""
    try:
        audit_log = models.AuditLog(
            admin_user_id=admin_user_id,
            action=action,
            target_user_id=target_user_id,
            target_resource=target_resource,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit_log)
        db.commit()

        logger.info(
            f"AUDIT: {action} by {admin_user_id} on {target_resource} {target_user_id}",
            extra={
                "action": action,
                "admin_user_id": str(admin_user_id),
                "target_user_id": str(target_user_id),
                "ip_address": ip_address,
            },
        )
    except Exception as e:
        db.rollback()
        logger.error(
            f"AUDIT LOG FAILED: {action} by {admin_user_id}",
            extra={
                "action": action,
                "admin_user_id": str(admin_user_id),
                "error": str(e),
            },
        )
