"""Announcements and comments."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Announcement, AnnouncementComment, UserRole
from routes.access import role_required
from services.activity import log_activity

bp = Blueprint("announcements", __name__)


@bp.route("/announcements")
@login_required
def announcements_list():
    rows = Announcement.query.order_by(Announcement.posted_at.desc()).all()
    return render_template("announcements/list.html", announcements=rows)


@bp.route("/announcements/new", methods=["GET", "POST"])
@role_required(UserRole.instructor)
def announcements_new():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        message = (request.form.get("message") or "").strip()
        if not title or not message:
            flash("Title and message are required.", "danger")
            return render_template("announcements/form.html")
        a = Announcement(title=title, message=message, posted_by=current_user.id)
        db.session.add(a)
        db.session.flush()
        log_activity("create_announcement", target_type="announcement", target_id=a.id)
        db.session.commit()
        flash("Announcement posted.", "success")
        return redirect(url_for("announcements.announcements_list"))
    return render_template("announcements/form.html")


@bp.route("/announcements/<int:announcement_id>")
@login_required
def announcements_detail(announcement_id: int):
    a = Announcement.query.get_or_404(announcement_id)
    comments = a.comments.order_by(AnnouncementComment.commented_at.asc()).all()
    return render_template("announcements/detail.html", announcement=a, comments=comments)


@bp.route("/announcements/<int:announcement_id>/comment", methods=["POST"])
@role_required(UserRole.student, UserRole.instructor)
def announcements_comment(announcement_id: int):
    a = Announcement.query.get_or_404(announcement_id)
    text = (request.form.get("comment_text") or "").strip()
    if not text:
        flash("Comment cannot be empty.", "warning")
        return redirect(url_for("announcements.announcements_detail", announcement_id=a.id))
    c = AnnouncementComment(announcement_id=a.id, user_id=current_user.id, comment_text=text)
    db.session.add(c)
    db.session.flush()
    log_activity("comment", target_type="announcement_comment", target_id=c.id)
    db.session.commit()
    flash("Comment added.", "success")
    return redirect(url_for("announcements.announcements_detail", announcement_id=a.id))
