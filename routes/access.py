"""Role-based access helpers."""
from functools import wraps

from flask import abort, redirect, url_for
from flask_login import current_user

from models import UserRole


def role_required(*roles: UserRole):
    """Ensure user is logged in and has one of the allowed roles."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
