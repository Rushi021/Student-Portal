"""Simple quizzes: instructor creates; student submits text; instructor grades."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Quiz, QuizSubmission, UserRole
from routes.access import role_required
from services.activity import log_activity

bp = Blueprint("quizzes", __name__)


@bp.route("/quizzes")
@login_required
def quizzes_list():
    rows = Quiz.query.order_by(Quiz.created_at.desc()).all()
    subs = {}
    if current_user.role == UserRole.student:
        for q in rows:
            sub = QuizSubmission.query.filter_by(quiz_id=q.id, student_id=current_user.id).first()
            subs[q.id] = sub
    return render_template("quizzes/list.html", quizzes=rows, submissions=subs)


@bp.route("/quizzes/new", methods=["GET", "POST"])
@role_required(UserRole.instructor)
def quizzes_new():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        if not title:
            flash("Title is required.", "danger")
            return render_template("quizzes/form.html")
        q = Quiz(title=title, description=description or None, created_by=current_user.id)
        db.session.add(q)
        db.session.commit()
        flash("Quiz created.", "success")
        return redirect(url_for("quizzes.quizzes_list"))
    return render_template("quizzes/form.html")


@bp.route("/quizzes/<int:quiz_id>")
@role_required(UserRole.student)
def quizzes_take(quiz_id: int):
    q = Quiz.query.get_or_404(quiz_id)
    existing = QuizSubmission.query.filter_by(quiz_id=q.id, student_id=current_user.id).first()
    return render_template("quizzes/take.html", quiz=q, submission=existing)


@bp.route("/quizzes/<int:quiz_id>/submit", methods=["POST"])
@role_required(UserRole.student)
def quizzes_submit(quiz_id: int):
    q = Quiz.query.get_or_404(quiz_id)
    text = (request.form.get("submission_text") or "").strip()
    if not text:
        flash("Please enter your answers.", "danger")
        return redirect(url_for("quizzes.quizzes_take", quiz_id=q.id))
    sub = QuizSubmission.query.filter_by(quiz_id=q.id, student_id=current_user.id).first()
    if sub:
        sub.submission_text = text
        sub.score = None
        sub.graded_by = None
    else:
        sub = QuizSubmission(quiz_id=q.id, student_id=current_user.id, submission_text=text)
        db.session.add(sub)
    db.session.flush()
    log_activity("take_quiz", target_type="quiz_submission", target_id=sub.id)
    db.session.commit()
    flash("Submission saved. Your instructor will grade it.", "success")
    return redirect(url_for("quizzes.quizzes_list"))


@bp.route("/quizzes/<int:quiz_id>/submissions")
@role_required(UserRole.instructor)
def quizzes_submissions(quiz_id: int):
    q = Quiz.query.get_or_404(quiz_id)
    if q.created_by != current_user.id:
        flash("You can only grade your own quizzes.", "danger")
        return redirect(url_for("quizzes.quizzes_list"))
    rows = QuizSubmission.query.filter_by(quiz_id=q.id).order_by(QuizSubmission.submitted_at.desc()).all()
    return render_template("quizzes/submissions.html", quiz=q, submissions=rows)


@bp.route("/quizzes/<int:quiz_id>/grade/<int:submission_id>", methods=["GET", "POST"])
@role_required(UserRole.instructor)
def quizzes_grade(quiz_id: int, submission_id: int):
    q = Quiz.query.get_or_404(quiz_id)
    if q.created_by != current_user.id:
        flash("You can only grade your own quizzes.", "danger")
        return redirect(url_for("quizzes.quizzes_list"))
    sub = QuizSubmission.query.filter_by(id=submission_id, quiz_id=q.id).first_or_404()
    if request.method == "POST":
        raw = (request.form.get("score") or "").strip()
        try:
            score = float(raw)
        except ValueError:
            flash("Score must be a number.", "danger")
            return render_template("quizzes/grade.html", quiz=q, submission=sub)
        sub.score = score
        sub.graded_by = current_user.id
        log_activity("grade_quiz", target_type="quiz_submission", target_id=sub.id)
        db.session.commit()
        flash("Grade saved.", "success")
        return redirect(url_for("quizzes.quizzes_submissions", quiz_id=q.id))
    return render_template("quizzes/grade.html", quiz=q, submission=sub)
