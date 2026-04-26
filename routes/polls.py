"""Simple polls: instructor creates a question; students respond once."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from sqlalchemy import func

from extensions import db
from models import Poll, PollResponse, UserRole
from routes.access import role_required
from services.activity import log_activity

bp = Blueprint("polls", __name__)


@bp.route("/polls")
@login_required
def polls_list():
    rows = Poll.query.order_by(Poll.created_at.desc()).all()
    responses = {}
    if current_user.role == UserRole.student:
        for p in rows:
            r = PollResponse.query.filter_by(poll_id=p.id, student_id=current_user.id).first()
            responses[p.id] = r
    counts = (
        db.session.query(PollResponse.poll_id, func.count(PollResponse.id))
        .group_by(PollResponse.poll_id)
        .all()
    )
    poll_counts = {pid: n for pid, n in counts}
    return render_template(
        "polls/list.html",
        polls=rows,
        responses=responses,
        poll_counts=poll_counts,
    )


@bp.route("/polls/new", methods=["GET", "POST"])
@role_required(UserRole.instructor)
def polls_new():
    if request.method == "POST":
        question = (request.form.get("question") or "").strip()
        if not question:
            flash("Question is required.", "danger")
            return render_template("polls/form.html")
        p = Poll(question=question, created_by=current_user.id)
        db.session.add(p)
        db.session.commit()
        flash("Poll created.", "success")
        return redirect(url_for("polls.polls_list"))
    return render_template("polls/form.html")


@bp.route("/polls/<int:poll_id>/respond", methods=["POST"])
@role_required(UserRole.student)
def polls_respond(poll_id: int):
    p = Poll.query.get_or_404(poll_id)
    choice = (request.form.get("response") or "").strip()
    if not choice:
        flash("Please enter a response.", "danger")
        return redirect(url_for("polls.polls_list"))
    existing = PollResponse.query.filter_by(poll_id=p.id, student_id=current_user.id).first()
    if existing:
        flash("You already responded to this poll.", "info")
        return redirect(url_for("polls.polls_list"))
    r = PollResponse(poll_id=p.id, student_id=current_user.id, response=choice)
    db.session.add(r)
    db.session.flush()
    log_activity("submit_poll", target_type="poll_response", target_id=r.id)
    db.session.commit()
    flash("Response recorded.", "success")
    return redirect(url_for("polls.polls_list"))
