"""HTTP smoke tests. Run from project root: python verify_e2e.py

Assumes: pip install -r requirements.txt, flask init-db, flask seed-db, flask seed-demo
"""
from __future__ import annotations

from app import app
from extensions import db
from models import Material, User, UserRole


def login(c, email: str, password: str) -> bool:
    r = c.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    return r.status_code in (301, 302, 303, 307, 308)


def main() -> None:
    c = app.test_client()

    # Anonymous
    r0 = c.get("/")
    assert r0.status_code in (301, 302, 303, 307, 308), "unauthenticated /"
    r_login = c.get("/login")
    assert r_login.status_code == 200, "GET /login"
    r_mat = c.get("/materials", follow_redirects=False)
    assert r_mat.status_code in (301, 302, 303, 307, 308), "anon /materials should redirect to login"

    # Student
    assert login(c, "student@whiteboard.edu", "student123"), "student login"
    assert c.get("/").status_code in (301, 302, 303, 307, 308)
    assert c.get("/student/dashboard").status_code == 200
    assert c.get("/admin/users").status_code == 403
    assert c.get("/instructor/dashboard").status_code == 403
    assert c.get("/materials").status_code == 200
    c.get("/logout", follow_redirects=True)

    # Student material view (after seed-demo)
    with app.app_context():
        m = Material.query.filter_by(title="Sample lecture (seed PDF)").first()
        mat_id = m.id if m else None
    if mat_id is not None:
        assert login(c, "student@whiteboard.edu", "student123")
        r_view = c.get(f"/materials/{mat_id}/view", follow_redirects=False)
        assert r_view.status_code == 200, f"view PDF: {r_view.status_code}"
        r_down = c.get(f"/materials/{mat_id}/download", follow_redirects=False)
        assert r_down.status_code == 200, f"download PDF: {r_down.status_code}"
        assert (r_view.mimetype or "").lower() in ("application/pdf", "application/octet-stream")
        c.get("/logout", follow_redirects=True)

    # Instructor
    assert login(c, "instructor@whiteboard.edu", "instructor123")
    assert c.get("/instructor/dashboard").status_code == 200
    assert c.get("/materials/upload").status_code == 200
    assert c.get("/admin/users").status_code == 403
    c.get("/logout", follow_redirects=True)

    # Admin
    assert login(c, "admin@whiteboard.edu", "admin123")
    assert c.get("/admin/users").status_code == 200
    assert c.get("/admin/users/new").status_code == 200
    assert c.get("/student/dashboard").status_code == 403
    c.get("/logout", follow_redirects=True)

    # users exist
    with app.app_context():
        assert User.query.filter_by(role=UserRole.student).count() >= 1
        assert User.query.filter_by(role=UserRole.instructor).count() >= 1
        assert User.query.filter_by(role=UserRole.admin).count() >= 1

    print("verify_e2e: OK")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    main()
