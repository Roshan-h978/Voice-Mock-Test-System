# Voice Mock Test - backend (Django REST API)

## Run it (Windows PowerShell)

Needs Python 3.11 or newer (3.14 works). Open PowerShell **in this `backend` folder**:

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

- If PowerShell blocks `Activate.ps1`: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, answer **Y**, activate again.
- Next time you only need `.\.venv\Scripts\Activate.ps1` and `python manage.py runserver`.
- Check it works: http://127.0.0.1:8000/api/health/ shows `{"status": "ok", ...}`.
- The settings file `backend/.env` is already filled in for your computer (SQLite database, demo scoring, emails printed in this window).

## Accounts

| Account | Email | Password | Created by |
| --- | --- | --- | --- |
| Admin | admin@example.com | admin123 | `python manage.py migrate` |
| Demo student | student@example.com | student123 | `python manage.py seed_demo` (development only) |

Change the admin password after the first sign-in: **Profile → Change password** (the dashboard reminds you).
Lost the admin? `python manage.py create_admin --email you@example.com --password something-new`

Raw data (all tables) is in the Django admin: http://127.0.0.1:8000/admin/ with the admin account.

## Connect PostgreSQL

The app uses SQLite (`backend/db.sqlite3`) until you set `DATABASE_URL` in `backend/.env`. The tables are created by `python manage.py migrate`; you don't write any SQL yourself.

### A. PostgreSQL on your own computer

1. Download PostgreSQL 16 or 17 for Windows from https://www.postgresql.org/download/windows/ (the EDB installer) and run it.
   Keep port **5432**, choose a password for the `postgres` user and remember it. pgAdmin is installed too.
2. Create the database. Open **SQL Shell (psql)** from the Start menu, press Enter for the defaults, type your password, then:
   ```
   CREATE DATABASE voice_mock_test;
   ```
   (Or in pgAdmin: Servers → PostgreSQL → Databases → right-click → Create → Database → name `voice_mock_test`.)
3. In `backend/.env` set:
   ```
   DATABASE_URL=postgres://postgres:YOUR_PASSWORD@localhost:5432/voice_mock_test
   ```
   If the password has special characters, replace them: `@` → `%40`, `#` → `%23`, `/` → `%2F`, `:` → `%3A`, `%` → `%25`.
4. Stop the backend (Ctrl+C), then:
   ```
   python manage.py migrate
   python manage.py seed_demo
   python manage.py runserver
   ```
   `migrate` creates every table and the admin account (admin@example.com / admin123).
5. Check: `python manage.py showmigrations` lists every migration with `[X]`, and pgAdmin shows tables such as `accounts_user`, `tests_manager_mocktest`, `attempts_attempt` under voice_mock_test → Schemas → public → Tables.

### B. Supabase (hosted PostgreSQL)

1. Create a project at https://supabase.com and set a database password.
2. Click **Connect** (top of the project page) → **Session pooler** → copy the URI. It looks like
   `postgresql://postgres.abcdefgh:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`
3. In `backend/.env`, paste it with your password and add `?sslmode=require`:
   ```
   DATABASE_URL=postgresql://postgres.abcdefgh:YOUR_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require
   ```
4. Run `python manage.py migrate`, `python manage.py seed_demo`, `python manage.py runserver`.
5. Your tables appear in Supabase under **Table Editor**.

Use the **Session pooler** (port 5432), not the Transaction pooler (6543).

### Optional: copy what you created in SQLite to PostgreSQL

Before changing `DATABASE_URL`:
```
python -X utf8 manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e admin.LogEntry -e sessions -e token_blacklist --indent 2 -o data.json
```
(`-X utf8` makes Windows save the file as UTF-8, so names and transcripts with special characters load correctly.)
Then set `DATABASE_URL`, run `python manage.py migrate`, then `python manage.py loaddata data.json`.
Recordings stay in `backend/media` (copy that folder too if you move computers).

## Google sign-in

1. Go to https://console.cloud.google.com → create a project.
2. **APIs & Services → OAuth consent screen**: choose **External**, fill in the app name and your email, save.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID** → type **Web application**.
4. Under **Authorized JavaScript origins** add `http://localhost:5173` and `http://localhost` (later also your real site, e.g. `https://your-domain.com`). No redirect URI is needed.
5. Copy the **Client ID** (ends with `.apps.googleusercontent.com`) into `backend/.env`:
   ```
   GOOGLE_CLIENT_ID=1234567890-abc123.apps.googleusercontent.com
   ```
6. Restart the backend. The **Continue with Google** button appears on the sign-in and sign-up pages.

Open the site as **http://localhost:5173** (not 127.0.0.1), because that is the origin you added in Google.
New Google users become students. Someone who already has an account with the same email signs in to that account. Invitation links work with Google too.

## Real scoring and email

- Scoring, free: get a key at https://console.groq.com/keys, then set `EVALUATION_DEMO_MODE=False`, `AI_PROVIDER=groq`, `GROQ_API_KEY=gsk_...` and restart. Groq's free tier covers roughly 30 full tests a day.
- Free backup (optional): get a key at https://aistudio.google.com/apikey and set `GEMINI_API_KEY=...`. When Groq is busy or over its free limit, Gemini writes the feedback instead.
- Check everything with **Test AI connection** under **Setup check** on the admin dashboard. It works in demo mode too.
- Scoring, paid: set `EVALUATION_DEMO_MODE=False`, `AI_PROVIDER=openai`, `OPENAI_API_KEY=...`, `ANTHROPIC_API_KEY=...` and restart.
- The admin dashboard's **Setup check** shows which service and models are in use.
- Email (Gmail): `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST_USER=you@gmail.com`, `EMAIL_HOST_PASSWORD=<16-character app password>`, `DEFAULT_FROM_EMAIL=Voice Mock Test <you@gmail.com>`; then use **Send me a test email** on the admin dashboard.

## Tests

```
python manage.py test
```

## Folder guide

| Folder | What's inside |
| --- | --- |
| `config/` | settings (reads `backend/.env`), URLs |
| `apps/accounts/` | users, roles, sign-in, Google sign-in, invitations, password reset, `create_admin` |
| `apps/tests_manager/` | mock tests, questions, `seed_demo` |
| `apps/attempts/` | taking tests, answers, results, reviews, dashboard numbers, reports |
| `apps/evaluation/` | speech-to-text, scoring rules, written feedback |
| `apps/notifications/` | emails and endpoints for optional n8n automations |
| `apps/common/` | shared helpers and permissions |

The API is served under `/api/`; the frontend's `src/services/` folder shows every call it makes.
