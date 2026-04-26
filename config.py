"""Application configuration.

Environment variables drive local vs AWS-oriented settings.
Load order: ``load_dotenv()`` runs at import so ``DATABASE_URL`` from ``.env`` is visible
before ``create_app`` reads the config classes.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).resolve().parent
_DEFAULT_SQLITE = f"sqlite:///{_ROOT / 'whiteboard_dev.db'}"


def _database_url() -> str:
    """Prefer ``DATABASE_URL``; default to file-based SQLite for local dev."""
    return os.environ.get("DATABASE_URL", _DEFAULT_SQLITE).strip()


def _is_sqlite(uri: str) -> bool:
    return uri.startswith("sqlite:")


def sqlalchemy_engine_options(uri: str) -> dict | None:
    """Connection pool tuned for PostgreSQL (e.g. RDS). Not used for SQLite."""
    if _is_sqlite(uri):
        return None
    return {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Local uploads directory when USE_S3 is false
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(_ROOT / "uploads"))

    # AWS / storage (see services/storage.py)
    USE_S3 = os.environ.get("USE_S3", "false").lower() in ("1", "true", "yes")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")
    S3_MATERIALS_PREFIX = os.environ.get("S3_MATERIALS_PREFIX", "materials/")
    S3_PRESIGN_EXPIRES = int(os.environ.get("S3_PRESIGN_EXPIRES", "3600"))

    # CloudWatch (see services/cloudwatch.py)
    CLOUDWATCH_LOG_GROUP = os.environ.get("CLOUDWATCH_LOG_GROUP", "/whiteboard/app")
    CLOUDWATCH_METRIC_NAMESPACE = os.environ.get("CLOUDWATCH_METRIC_NAMESPACE", "Whiteboard/App")
    ENABLE_CLOUDWATCH = os.environ.get("ENABLE_CLOUDWATCH", "false").lower() in ("1", "true", "yes")

    # Production-style cookies / URLs (set on Elastic Beanstalk behind HTTPS)
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    PREFERRED_URL_SCHEME = os.environ.get("PREFERRED_URL_SCHEME", "http")


class DevelopmentConfig(BaseConfig):
    """Local dev: SQLite by default, or PostgreSQL if ``DATABASE_URL`` is set."""

    DEBUG = True
    FLASK_ENV = "development"

    SQLALCHEMY_DATABASE_URI = _database_url()


_prod_db_uri = os.environ.get("DATABASE_URL", "").strip()


class ProductionConfig(BaseConfig):
    """AWS (Elastic Beanstalk / EC2): requires ``DATABASE_URL`` (RDS PostgreSQL)."""

    DEBUG = False
    FLASK_ENV = "production"

    SQLALCHEMY_DATABASE_URI = _prod_db_uri


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
