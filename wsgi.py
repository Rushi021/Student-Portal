"""WSGI entry for Gunicorn / AWS Elastic Beanstalk (Python platform).

Elastic Beanstalk looks for a callable named ``application`` by default.
Re-use the app created in ``app.py`` (single process-wide instance).
"""
from app import app as application
