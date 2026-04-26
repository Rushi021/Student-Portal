"""Whiteboard — Flask app (local-first; AWS-ready via env — see README).

**Local (SQLite + disk):**
  export FLASK_APP=app.py
  flask db upgrade
  flask seed-db
  flask seed-demo
  flask run

**Migrations** replace ad-hoc ``init-db`` for deploys; ``flask init-db`` still calls ``create_all`` for quick scratch DBs.
"""
from __future__ import annotations

import os

from flask import Flask, redirect, render_template, url_for
from flask_login import current_user

from config import config_by_name, sqlalchemy_engine_options
from extensions import db, login_manager, migrate
from models import (
    Announcement,
    Course,
    CourseEnrollment,
    Material,
    Poll,
    Quiz,
    User,
    UserRole,
)
from routes.admin_routes import bp as admin_bp
from routes.announcements import bp as announcements_bp
from routes.auth import bp as auth_bp
from routes.courses import bp as courses_bp
from routes.instructor import bp as instructor_bp
from routes.materials import bp as materials_bp
from routes.polls import bp as polls_bp
from routes.quizzes import bp as quizzes_bp
from routes.student import bp as student_bp


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    cfg = config_name or os.environ.get("FLASK_ENV", "development")
    if cfg == "production":
        config_cls = config_by_name["production"]
    else:
        config_cls = config_by_name.get(cfg, config_by_name["development"])
    app.config.from_object(config_cls)
    if config_cls is config_by_name["production"] and not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise ValueError("DATABASE_URL must be set when FLASK_ENV=production (e.g. RDS connection string).")

    db_uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").strip()
    _eo = sqlalchemy_engine_options(db_uri)
    if _eo:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = _eo

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(instructor_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(quizzes_bp)
    app.register_blueprint(polls_bp)

    @app.route("/")
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role == UserRole.student:
            return redirect(url_for("student.dashboard"))
        if current_user.role == UserRole.instructor:
            return redirect(url_for("instructor.dashboard"))
        return redirect(url_for("admin.dashboard"))

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.cli.command("init-db")
    def init_db():
        """Create tables without running Alembic (quick local scratch). Prefer ``flask db upgrade``."""
        db.create_all()
        print("Tables created. For team/deploy workflows use: flask db upgrade")

    @app.cli.command("seed-db")
    def seed_db():
        """Seed demo users (student, instructor, admin) and requested class users."""
        db.create_all()
        created = 0
        if User.query.filter_by(email="student@whiteboard.edu").first():
            pass
        else:
            student = User(name="Demo Student", email="student@whiteboard.edu", role=UserRole.student)
            student.set_password("student123")
            instructor = User(
                name="Demo Instructor",
                email="instructor@whiteboard.edu",
                role=UserRole.instructor,
            )
            instructor.set_password("instructor123")
            admin = User(name="Demo Admin", email="admin@whiteboard.edu", role=UserRole.admin)
            admin.set_password("admin123")
            db.session.add_all([student, instructor, admin])
            created += 3

        requested_users = [
            ("Student One", "student1@whiteboard.edu", "student1231", UserRole.student),
            ("Student Two", "student2@whiteboard.edu", "student1232", UserRole.student),
            ("Student Three", "student3@whiteboard.edu", "student1233", UserRole.student),
            ("Instructor One", "instructor1@whiteboard.edu", "instructor1231", UserRole.instructor),
            ("Instructor Two", "instructor2@whiteboard.edu", "instructor1232", UserRole.instructor),
            ("Admin One", "admin1@whiteboard.edu", "admin1231", UserRole.admin),
        ]
        for name, email, password, role in requested_users:
            existing = User.query.filter_by(email=email).first()
            if existing:
                continue
            u = User(name=name, email=email, role=role)
            u.set_password(password)
            db.session.add(u)
            created += 1
        db.session.commit()
        if created == 0:
            print("No new users created (seed data already present).")
            return
        print(f"Seeded users. New users created: {created}")
        print("  student@whiteboard.edu / student123")
        print("  instructor@whiteboard.edu / instructor123")
        print("  admin@whiteboard.edu / admin123")
        print("  student1@whiteboard.edu / student1231")
        print("  student2@whiteboard.edu / student1232")
        print("  student3@whiteboard.edu / student1233")
        print("  instructor1@whiteboard.edu / instructor1231")
        print("  instructor2@whiteboard.edu / instructor1232")
        print("  admin1@whiteboard.edu / admin1231")

    @app.cli.command("seed-courses")
    def seed_courses():
        """Seed 2 courses and enroll the 3 requested students in both courses."""
        db.create_all()
        inst1 = User.query.filter_by(email="instructor1@whiteboard.edu").first()
        inst2 = User.query.filter_by(email="instructor2@whiteboard.edu").first()
        students = [
            User.query.filter_by(email="student1@whiteboard.edu").first(),
            User.query.filter_by(email="student2@whiteboard.edu").first(),
            User.query.filter_by(email="student3@whiteboard.edu").first(),
        ]
        if not inst1 or not inst2 or any(s is None for s in students):
            print("Run flask seed-db first.")
            return

        catalog = [
            ("IST.615.M001", "Cloud Management", "Spring 2026", inst1.id),
            ("IST.691.M001", "Deep Learning", "Spring 2026", inst2.id),
        ]
        created = 0
        target_course_ids: list[int] = []
        for code, title, term, instructor_id in catalog:
            c = Course.query.filter_by(code=code, term=term).first()
            if not c:
                c = Course(
                    code=code,
                    title=title,
                    term=term,
                    instructor_id=instructor_id,
                    image_url=None,
                    is_active=True,
                )
                db.session.add(c)
                db.session.flush()
                created += 1
            else:
                c.title = title
                c.instructor_id = instructor_id
                c.is_active = True
            target_course_ids.append(c.id)
            for student in students:
                en = CourseEnrollment.query.filter_by(course_id=c.id, student_id=student.id).first()
                if not en:
                    db.session.add(CourseEnrollment(course_id=c.id, student_id=student.id))

        # Ensure requested students only keep the two target courses.
        for student in students:
            extra = (
                CourseEnrollment.query.filter_by(student_id=student.id)
                .filter(~CourseEnrollment.course_id.in_(target_course_ids))
                .all()
            )
            for row in extra:
                db.session.delete(row)

        # Keep only the two target courses for the seeded term.
        old_courses = (
            Course.query.filter_by(term="Spring 2026")
            .filter(~Course.id.in_(target_course_ids))
            .all()
        )
        for oc in old_courses:
            CourseEnrollment.query.filter_by(course_id=oc.id).delete()
            db.session.delete(oc)
        db.session.commit()
        print(f"Seeded courses. New courses created: {created}. Students now have exactly 2 courses each.")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Optional demo: announcement, quiz, poll, and a sample PDF (``uploads/`` or S3 when ``USE_S3``)."""
        from services.seed_helpers import build_sample_pdf_bytes
        from services.storage import get_storage

        db.create_all()
        inst = User.query.filter_by(email="instructor@whiteboard.edu").first()
        if not inst:
            print("Run flask seed-db first (instructor@whiteboard.edu missing).")
            return
        n = 0
        if not Announcement.query.filter_by(title="Welcome to Whiteboard").first():
            db.session.add(
                Announcement(
                    title="Welcome to Whiteboard",
                    message="This is a sample announcement. Instructors can post new ones from the dashboard.",
                    posted_by=inst.id,
                )
            )
            n += 1
        if not Quiz.query.filter_by(title="Sample weekly check-in").first():
            db.session.add(
                Quiz(
                    title="Sample weekly check-in",
                    description="In one short paragraph, name one idea from the last lecture and one question you still have.",
                    created_by=inst.id,
                )
            )
            n += 1
        if not Poll.query.filter_by(question="How useful was last week's content? (demo poll)").first():
            db.session.add(
                Poll(
                    question="How useful was last week's content? (demo poll)",
                    created_by=inst.id,
                )
            )
            n += 1
        if not Material.query.filter_by(title="Sample lecture (seed PDF)").first():
            storage = get_storage()
            file_key = storage.save_pdf_bytes(build_sample_pdf_bytes(), "sample-lecture.pdf")
            db.session.add(
                Material(
                    title="Sample lecture (seed PDF)",
                    file_url=file_key,
                    uploaded_by=inst.id,
                )
            )
            n += 1
        if n:
            db.session.commit()
            print(f"Seeded {n} demo item(s) (may include sample PDF, announcement, quiz, poll).")
        else:
            print("Demo content already present; nothing to add.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
