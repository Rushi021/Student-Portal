"""Instructor dashboard."""
from flask import Blueprint, render_template
from flask_login import current_user

from models import Announcement, Material, Poll, Quiz, UserRole
from routes.access import role_required

bp = Blueprint("instructor", __name__, url_prefix="/instructor")


@bp.route("/dashboard")
@role_required(UserRole.instructor)
def dashboard():
    my_materials = Material.query.filter_by(uploaded_by=current_user.id).count()
    my_quizzes = Quiz.query.filter_by(created_by=current_user.id).count()
    my_announcements = Announcement.query.filter_by(posted_by=current_user.id).count()
    my_polls = Poll.query.filter_by(created_by=current_user.id).count()
    return render_template(
        "instructor/dashboard.html",
        user=current_user,
        my_materials=my_materials,
        my_quizzes=my_quizzes,
        my_announcements=my_announcements,
        my_polls=my_polls,
    )
