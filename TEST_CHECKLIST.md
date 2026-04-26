# Whiteboard — manual test checklist

Use with `flask run` at `http://127.0.0.1:5000`. Accounts from `flask seed-db` (and run `flask seed-demo` for sample course content and a **Sample lecture (seed PDF)**).

| Role   | Email                     | Password        |
|--------|---------------------------|-----------------|
| Student| `student@whiteboard.edu`  | `student123`    |
| Instructor | `instructor@whiteboard.edu` | `instructor123` |
| Admin  | `admin@whiteboard.edu`    | `admin123`      |

## Automated smoke test

```bash
pip install -r requirements.txt
export FLASK_APP=app.py
flask init-db
flask seed-db
flask seed-demo
python verify_e2e.py
```

## Student

- [ ] Log in; lands on **Student dashboard**; **Logout** returns to login.
- [ ] **Materials** — list loads; open **View** and **Download** for *Sample lecture (seed PDF)* (HTTP 200, PDF in browser or download).
- [ ] **Quizzes** — open *Sample weekly check-in*; submit a short answer; list shows *Submitted* (and score after instructor grades).
- [ ] **Polls** — answer *How useful was last week's content?* once; a second try shows a flash that you already responded.
- [ ] **Announcements** — list and open *Welcome to Whiteboard*; post a **comment** (if your policy allows only student+instructor, admin should not see a comment form).
- [ ] Open `/admin/users` — expect **403 Forbidden**.

## Instructor

- [ ] **Dashboard** links work; **Upload PDF** — upload a real `.pdf` and see it in **Materials**.
- [ ] **New** announcement, quiz, and poll; each appears in the right list.
- [ ] **Quizzes** — for a quiz you created, use **Grade** to open a submission and set a **score**; log in as student and confirm the score shows.
- [ ] **Users** at `/admin/users` — expect **403**.

## Admin

- [ ] **Users** — list, **New user** (e.g. test role `student`), **Edit** (name/email/role/optional new password), **Delete** a non–self test user.
- [ ] **Student** routes (e.g. `/student/dashboard`) — expect **403** for admin in this app’s role model.

## Cross-cutting

- [ ] Not logged in: hitting `/` or protected URLs redirects toward **login** (or 401/302 as configured).
- [ ] **403** page has a way back (**Home**).
- [ ] (Deployment) WSGI: `gunicorn wsgi:application` — `wsgi` imports a single `application` from `app.app`.
