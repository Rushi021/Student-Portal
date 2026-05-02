"""Admin dashboard and user management."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func

from extensions import db
from models import Course, CourseEnrollment, User, UserRole
from routes.access import role_required
from services.activity import log_activity

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _enroll_student_in_all_courses(student_id: int) -> None:
    for course in Course.query.filter_by(is_active=True).all():
        exists = CourseEnrollment.query.filter_by(course_id=course.id, student_id=student_id).first()
        if not exists:
            db.session.add(CourseEnrollment(course_id=course.id, student_id=student_id))


def _enroll_all_students_in_course(course_id: int) -> None:
    for student in User.query.filter_by(role=UserRole.student).all():
        exists = CourseEnrollment.query.filter_by(course_id=course_id, student_id=student.id).first()
        if not exists:
            db.session.add(CourseEnrollment(course_id=course_id, student_id=student.id))


@bp.route("/dashboard")
@role_required(UserRole.admin)
def dashboard():
    return redirect(url_for("admin.users_list"))


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
        if role == UserRole.student:
            _enroll_student_in_all_courses(u.id)
        log_activity("create_user", target_type="user", target_id=u.id)
        db.session.commit()
        flash("User created.", "success")
        return redirect(url_for("admin.users_list"))
    return render_template("admin/user_form.html", user=None)


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@role_required(UserRole.admin)
def users_edit(user_id: int):
    u = User.query.get_or_404(user_id)
    prior_role = u.role
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
        if u.role == UserRole.student and prior_role != UserRole.student:
            _enroll_student_in_all_courses(u.id)
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


@bp.route("/courses")
@role_required(UserRole.admin)
def courses_list():
    courses = Course.query.order_by(Course.term.desc(), Course.code.asc()).all()
    counts = (
        db.session.query(CourseEnrollment.course_id, func.count(CourseEnrollment.id))
        .group_by(CourseEnrollment.course_id)
        .all()
    )
    enrollment_counts = {course_id: n for course_id, n in counts}
    return render_template(
        "admin/courses.html",
        courses=courses,
        enrollment_counts=enrollment_counts,
    )


@bp.route("/courses/new", methods=["GET", "POST"])
@role_required(UserRole.admin)
def courses_new():
    instructors = User.query.filter_by(role=UserRole.instructor).order_by(User.name.asc()).all()
    if request.method == "POST":
        code = (request.form.get("code") or "").strip()
        title = (request.form.get("title") or "").strip()
        term = (request.form.get("term") or "Spring 2026").strip()
        image_url = (request.form.get("image_url") or "").strip() or None
        instructor_id = request.form.get("instructor_id", type=int)
        if not code or not title or not instructor_id:
            flash("Code, title, and instructor are required.", "danger")
            return render_template("admin/course_form.html", instructors=instructors)
        instructor = User.query.filter_by(id=instructor_id, role=UserRole.instructor).first()
        if not instructor:
            flash("Invalid instructor.", "danger")
            return render_template("admin/course_form.html", instructors=instructors)
        c = Course(
            code=code,
            title=title,
            term=term,
            image_url=image_url,
            is_active=True,
            instructor_id=instructor.id,
        )
        db.session.add(c)
        db.session.flush()
        _enroll_all_students_in_course(c.id)
        log_activity("create_course", target_type="course", target_id=c.id)
        db.session.commit()
        flash("Course created and all students enrolled.", "success")
        return redirect(url_for("admin.courses_list"))
    return render_template("admin/course_form.html", instructors=instructors)
