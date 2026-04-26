"""Student dashboard."""
from flask import Blueprint, render_template
from flask_login import current_user

from models import Announcement, Material, Poll, Quiz, UserRole
from routes.access import role_required

bp = Blueprint("student", __name__, url_prefix="/student")


@bp.route("/dashboard")
@role_required(UserRole.student)
def dashboard():
    materials_count = Material.query.count()
    quizzes_count = Quiz.query.count()
    announcements = Announcement.query.order_by(Announcement.posted_at.desc()).limit(5).all()
    open_polls = Poll.query.order_by(Poll.created_at.desc()).limit(5).all()
    return render_template(
        "student/dashboard.html",
        user=current_user,
        materials_count=materials_count,
        quizzes_count=quizzes_count,
        announcements=announcements,
        polls=open_polls,
    )
