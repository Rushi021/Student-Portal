"""Persist rows to activity_logs for demos and basic auditing.

Core action names (course spec): login, upload_material, download_material,
create_announcement, comment, take_quiz, submit_poll, create_user.

Additional actions used in this app: grade_quiz, update_user, delete_user.
"""
from flask import current_app
from flask_login import current_user

from extensions import db
from models import ActivityLog


def log_activity(action: str, target_type: str | None = None, target_id: int | None = None) -> None:
    """Record an action. Commits are left to the caller to batch with other writes."""
    uid = current_user.id if current_user.is_authenticated else None
    if current_app:
        current_app.logger.info(
            "activity user=%s action=%s target=%s:%s",
            uid,
            action,
            target_type,
            target_id,
        )
    row = ActivityLog(
        user_id=uid,
        action=action,
        target_type=target_type,
        target_id=target_id,
    )
    db.session.add(row)
    if current_app and current_app.config.get("ENABLE_CLOUDWATCH"):
        from services.cloudwatch import emit_activity_metric

        emit_activity_metric(action)
