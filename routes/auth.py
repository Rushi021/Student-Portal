"""Login / logout (Flask-Login sessions, role-based redirects)."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from extensions import db
from models import User, UserRole
from services.activity import log_activity

bp = Blueprint("auth", __name__)


def _dashboard_for_role(role: UserRole):
    if role == UserRole.student:
        return redirect(url_for("student.dashboard"))
    if role == UserRole.instructor:
        return redirect(url_for("instructor.dashboard"))
    return redirect(url_for("admin.dashboard"))


def _safe_next_redirect():
    """Allow only same-site relative paths (Flask-Login ``next`` query / form)."""
    target = (request.values.get("next") or "").strip()
    if target.startswith("/") and not target.startswith("//"):
        return redirect(target)
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _dashboard_for_role(current_user.role)

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            log_activity("login", target_type="user", target_id=user.id)
            db.session.commit()
            flash("Signed in.", "success")
            nxt = _safe_next_redirect()
            if nxt:
                return nxt
            return _dashboard_for_role(user.role)
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("auth.login"))
