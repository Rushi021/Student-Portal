"""Courses list pages for students/instructors/admin."""
from flask import Blueprint, render_template
from flask_login import current_user, login_required

from models import Course, CourseEnrollment, UserRole

bp = Blueprint("courses", __name__)


@bp.route("/courses")
@login_required
def courses_list():
    if current_user.role == UserRole.student:
        rows = (
            Course.query.join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
            .filter(CourseEnrollment.student_id == current_user.id)
            .order_by(Course.term.desc(), Course.code.asc())
            .all()
        )
    elif current_user.role == UserRole.instructor:
        rows = (
            Course.query.filter_by(instructor_id=current_user.id)
            .order_by(Course.term.desc(), Course.code.asc())
            .all()
        )
    else:
        rows = Course.query.order_by(Course.term.desc(), Course.code.asc()).all()
    return render_template("courses/list.html", courses=rows)
