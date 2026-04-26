"""Admin dashboard and user management."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from extensions import db
from models import User, UserRole
from routes.access import role_required
from services.activity import log_activity

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/dashboard")
@role_required(UserRole.admin)
def dashboard():
    user_count = User.query.count()
    return render_template("admin/dashboard.html", user=current_user, user_count=user_count)


@bp.route("/users")
@role_required(UserRole.admin)
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@bp.route("/users/new", methods=["GET", "POST"])
@role_required(UserRole.admin)
def users_new():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        role_str = (request.form.get("role") or "").strip().lower()
        if not name or not email or not password:
            flash("Name, email, and password are required.", "danger")
            return render_template("admin/user_form.html", user=None)
        try:
            role = UserRole(role_str)
        except ValueError:
            flash("Invalid role.", "danger")
            return render_template("admin/user_form.html", user=None)
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return render_template("admin/user_form.html", user=None)
        u = User(name=name, email=email, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.flush()
        log_activity("create_user", target_type="user", target_id=u.id)
        db.session.commit()
        flash("User created.", "success")
        return redirect(url_for("admin.users_list"))
    return render_template("admin/user_form.html", user=None)


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@role_required(UserRole.admin)
def users_edit(user_id: int):
    u = User.query.get_or_404(user_id)
    if request.method == "POST":
        u.name = (request.form.get("name") or u.name).strip()
        email = (request.form.get("email") or "").strip().lower()
        if email and email != u.email:
            if User.query.filter_by(email=email).first():
                flash("Email already in use.", "danger")
                return render_template("admin/user_form.html", user=u)
            u.email = email
        role_str = (request.form.get("role") or "").strip().lower()
        try:
            u.role = UserRole(role_str)
        except ValueError:
            flash("Invalid role.", "danger")
            return render_template("admin/user_form.html", user=u)
        pwd = request.form.get("password") or ""
        if pwd:
            u.set_password(pwd)
        log_activity("update_user", target_type="user", target_id=u.id)
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("admin.users_list"))
    return render_template("admin/user_form.html", user=u)


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@role_required(UserRole.admin)
def users_delete(user_id: int):
    u = User.query.get_or_404(user_id)
    if u.id == current_user.id:
        flash("You cannot delete your own account while logged in.", "danger")
        return redirect(url_for("admin.users_list"))
    db.session.delete(u)
    log_activity("delete_user", target_type="user", target_id=user_id)
    db.session.commit()
    flash("User deleted.", "info")
    return redirect(url_for("admin.users_list"))
