"""SQLAlchemy models for Whiteboard (local SQLite; PostgreSQL-ready via connection URL).

Relationship summary:
- User creates materials, quizzes, announcements, polls (via foreign keys).
- Students submit quiz_submissions and poll_responses.
- Announcements have announcement_comments.
- activity_logs records notable actions for auditing / demos.
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class UserRole(str, PyEnum):
    student = "student"
    instructor = "instructor"
    admin = "admin"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # native_enum=False keeps SQLite and PostgreSQL happy without PG enum types
    role = db.Column(
        db.Enum(
            UserRole,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
        ),
        nullable=False,
        default=UserRole.student,
    )
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    materials = db.relationship("Material", backref="uploader", lazy="dynamic")
    quizzes_created = db.relationship(
        "Quiz",
        foreign_keys="Quiz.created_by",
        backref="creator",
        lazy="dynamic",
    )
    announcements = db.relationship("Announcement", backref="author", lazy="dynamic")
    polls = db.relationship("Poll", backref="creator", lazy="dynamic")
    courses_taught = db.relationship("Course", backref="instructor", lazy="dynamic")
    course_enrollments = db.relationship("CourseEnrollment", backref="student", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    # Local path relative to upload folder, or S3 object key — see storage service
    file_url = db.Column(db.String(512), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Quiz(db.Model):
    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    submissions = db.relationship("QuizSubmission", backref="quiz", lazy="dynamic")


class QuizSubmission(db.Model):
    __tablename__ = "quiz_submissions"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # MVP: free-text answers; instructor grades manually (score + graded_by)
    submission_text = db.Column(db.Text, nullable=True)
    score = db.Column(db.Float, nullable=True)
    graded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    submitted_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    student = db.relationship("User", foreign_keys=[student_id])
    grader = db.relationship("User", foreign_keys=[graded_by])


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    posted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    posted_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    comments = db.relationship("AnnouncementComment", backref="announcement", lazy="dynamic")


class AnnouncementComment(db.Model):
    __tablename__ = "announcement_comments"

    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcements.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    commented_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("announcement_comments", lazy="dynamic"))


class Poll(db.Model):
    __tablename__ = "polls"

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    responses = db.relationship("PollResponse", backref="poll", lazy="dynamic")


class PollResponse(db.Model):
    __tablename__ = "poll_responses"

    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    response = db.Column(db.String(500), nullable=False)
    responded_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    student = db.relationship("User", backref=db.backref("poll_responses", lazy="dynamic"))


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(120), nullable=False)
    target_type = db.Column(db.String(64), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("activity_logs", lazy="dynamic"))


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    term = db.Column(db.String(64), nullable=False, default="Spring 2026")
    image_url = db.Column(db.String(512), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    enrollments = db.relationship("CourseEnrollment", backref="course", lazy="dynamic")


class CourseEnrollment(db.Model):
    __tablename__ = "course_enrollments"
    __table_args__ = (
        db.UniqueConstraint("course_id", "student_id", name="uq_course_student"),
    )

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=utcnow, nullable=False)
