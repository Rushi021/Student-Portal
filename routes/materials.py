"""Lecture materials: PDF upload (instructor) and listing / download (students)."""
import os

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from extensions import db
from models import Material, UserRole
from routes.access import role_required
from services.activity import log_activity
from services.storage import get_storage

bp = Blueprint("materials", __name__)


def _allowed_pdf(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "pdf"


@bp.route("/materials")
@login_required
def materials_list():
    items = Material.query.order_by(Material.uploaded_at.desc()).all()
    return render_template("materials/list.html", materials=items)


@bp.route("/materials/upload", methods=["GET", "POST"])
@role_required(UserRole.instructor)
def materials_upload():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        file = request.files.get("file")
        if not title or not file or not file.filename:
            flash("Title and PDF file are required.", "danger")
            return render_template("materials/upload.html")
        if not _allowed_pdf(file.filename):
            flash("Only PDF uploads are allowed.", "danger")
            return render_template("materials/upload.html")
        storage = get_storage()
        safe_name = secure_filename(file.filename)
        key = storage.save_pdf(file, safe_name)
        m = Material(title=title, file_url=key, uploaded_by=current_user.id)
        db.session.add(m)
        db.session.flush()
        log_activity("upload_material", target_type="material", target_id=m.id)
        db.session.commit()
        flash("Material uploaded.", "success")
        return redirect(url_for("materials.materials_list"))
    return render_template("materials/upload.html")


def _serve_material(material_id: int, as_attachment: bool):
    m = Material.query.get_or_404(material_id)
    storage = get_storage()
    kind, value = storage.download_url_or_path(
        m.file_url,
        download_name=f"{m.title}.pdf",
        as_attachment=as_attachment,
    )
    log_activity("download_material", target_type="material", target_id=m.id)
    db.session.commit()
    if kind == "redirect":
        return redirect(value)
    if not os.path.isfile(value):
        flash("File missing on server.", "danger")
        return redirect(url_for("materials.materials_list"))
    return send_file(
        value,
        as_attachment=as_attachment,
        download_name=f"{m.title}.pdf",
        mimetype="application/pdf",
    )


@bp.route("/materials/<int:material_id>/view")
@login_required
def materials_view(material_id: int):
    return _serve_material(material_id, as_attachment=False)


@bp.route("/materials/<int:material_id>/download")
@login_required
def materials_download(material_id: int):
    return _serve_material(material_id, as_attachment=True)
