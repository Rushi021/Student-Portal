# Whiteboard

Minimal **server-rendered** Flask app for a university **cloud management** project. Phase 2 is a **complete local** feature set; AWS (RDS, S3, CloudWatch, EC2/Elastic Beanstalk) is optional later.

## Phase 2 (complete): local app

| Area | Implementation |
|------|----------------|
| **Auth** | `routes/auth.py` — login, logout, `role_required` in `routes/access.py`, 403 for wrong role, redirects by role on `/` |
| **Dashboards** | `/student`, `/instructor`, `/admin` dashboard routes + templates |
| **Materials** | Instructors upload PDFs to `uploads/`; metadata in `materials`; students view and download; `services/storage.py` swappable for S3 |
| **Announcements** | Instructors create; all roles read; students and instructors comment |
| **Quizzes** | Instructors create and grade; students submit one text answer; `quiz_submissions` |
| **Polls** | Instructors create; students respond once |
| **Admin** | Create/edit/delete users, assign `student` / `instructor` / `admin` |
| **Activity log** | `activity_logs` + `services/activity.py` (see docstring for action names) |
| **DB** | Default SQLite `whiteboard_dev.db`; set `DATABASE_URL` for PostgreSQL (RDS) |

`boto3` is in `requirements.txt` for optional S3; it is not required for local development.

---

The longer-term **architecture story** is AWS: **RDS (PostgreSQL)**, **S3** (materials), and **CloudWatch** (logs/metrics), with the web tier on **Elastic Beanstalk** or **EC2**.

## What it does

- **Student:** login, download lecture PDFs, take simple text-based quizzes, read announcements and comment, respond to polls.
- **Instructor:** login, upload PDFs, post announcements, create quizzes and grade submissions, create polls.
- **Admin:** login, create/edit/delete users and assign roles (`student`, `instructor`, `admin`).

## Stack

- Flask, Jinja2, Bootstrap (CDN)
- SQLAlchemy + Flask-Login
- **Local:** SQLite + on-disk `uploads/` (default)
- **AWS-ready:** `boto3` S3 upload/presigned download; structured logging hook for CloudWatch; `DATABASE_URL` for RDS

## Project layout

- `app.py` — app factory, CLI: `flask init-db`, `flask seed-db`, `flask seed-demo` (optional sample content + **seed PDF** in `uploads/`)
- `verify_e2e.py` — `python verify_e2e.py` after seeding; `TEST_CHECKLIST.md` — short manual test guide by role
- `config.py` — environment-driven settings
- `models.py` — SQLAlchemy models
- `extensions.py` — `db`, `login_manager`
- `routes/` — blueprints (auth, student, instructor, admin, materials, announcements, quizzes, polls)
- `services/` — `storage` (local vs S3), `activity` (audit log), `cloudwatch` (optional hook)
- `templates/`, `static/`, `uploads/` (PDFs; tracked via `.gitkeep` only)

## Schema note

The `quiz_submissions` table includes a **`submission_text`** column so students can submit answers for a minimal “essay style” quiz. The instructor assigns a numeric **score** manually.

## Local setup

```bash
cd Whiteboard
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # optional; defaults work for SQLite
export FLASK_APP=app.py
flask init-db
flask seed-db
flask seed-demo
flask run
```

Open http://127.0.0.1:5000 and sign in:

| Role       | Email                      | Password       |
|-----------|----------------------------|----------------|
| Student   | `student@whiteboard.edu`   | `student123`   |
| Instructor| `instructor@whiteboard.edu`| `instructor123`|
| Admin     | `admin@whiteboard.edu`     | `admin123`     |

`flask seed-demo` adds a valid sample PDF (via `pypdf` + `services/seed_helpers.py`) and a `materials` row so **View** / **Download** work without a manual upload.

**Smoke test:** `python verify_e2e.py`

### Local PostgreSQL (optional)

Set `DATABASE_URL` to a `postgresql+psycopg2://...` URL and run `flask init-db` / `flask seed-db` again.

## AWS deployment (high level)

**Flow to present in class:** `User → Flask (Elastic Beanstalk or EC2) → RDS + S3 → CloudWatch`.

1. **RDS:** Create a PostgreSQL instance; set `DATABASE_URL` on the app environment to the RDS connection string (use the SQLAlchemy `postgresql+psycopg2://` form).
2. **S3:** Create a bucket; IAM role attached to the instance/EB environment with `s3:PutObject`, `s3:GetObject` on that bucket. Set `USE_S3=true`, `S3_BUCKET_NAME`, `AWS_REGION`, and optional `S3_MATERIALS_PREFIX`.
3. **CloudWatch:** Application logs go to stdout/stderr; Elastic Beanstalk can stream these to a log group. Set `ENABLE_CLOUDWATCH=true` if you extend `services/cloudwatch.py` with custom metrics or log shipping.
4. **Secrets:** Set `SECRET_KEY` and database credentials via environment properties (not committed). Use `.env` only on your laptop.

5. **WSGI:** For Gunicorn on EB or EC2, point the server at `wsgi:application` (see `wsgi.py`).

Code comments mark **AWS integration points** in `services/storage.py`, `services/cloudwatch.py`, and `config.py`.

## License / use

Academic demo — adapt as needed for your course submission.
