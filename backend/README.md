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

### What admins can manage

| | Create | View | Update | Delete |
| --- | --- | --- | --- | --- |
| People (**Students**) | **Add person** (with a starting password) or **Invite** by email | list, search, filters | **Edit**: name, level, role, phone, new password; **Suspend** | trash icon: the account with all its results and recordings |
| Tests (**Mock tests**) | **New test** | list, preview | **Edit**, publish, archive | trash icon; a test with results asks before deleting them too |
| Questions | **Add question** | per test | edit, reorder | delete |
| Results (**Reviews**) | taken by students | queue, filters | **Publish review**, score again | trash icon or **Delete result**: answers and recordings go too |

Admins can't delete or suspend their own account. People given a password by an admin are asked to choose their own after signing in.

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

### How answers are scored

- **Fluency** comes from pace, filler words and pauses, plus how well the ideas are linked. **Pronunciation** comes from how clearly the speech-to-text heard each word. **Grammar** comes from the AI examiner.
- The AI examiner first decides whether the answer responds to the question (yes, partly or no), then scores with a fixed rubric at temperature 0, so the same answer gets the same score.
- Scores follow the question: an off-topic answer can't score more than about 40%, a partly relevant one is limited by how relevant it is, and a short answer (about one word per second of speaking time earns full credit) is limited too. The student sees **Why this score is limited** under the answer.
- The limits are in `apps/evaluation/scoring.py` (`content_limit`) and `SCORING` in `config/settings.py`.

### AI-written questions

- Admins: **Write questions with AI** on a test's Questions page (suggestions to edit, untick or add), or **Questions written by AI** in the **New test** form.
- Students: **Quick practice** can ask the AI for a new question on a topic.
- Both use the same AI key as scoring. In demo mode the questions come from a built-in bank. Limits per person: `THROTTLE_AI` (default 30 an hour) for writing questions and `THROTTLE_PRACTICE` (default 60 an hour) for scoring practice answers.

### Student pages

| Page | What it does |
| --- | --- |
| Quick practice | One question (AI-written on a topic, or from the published tests), record, feedback straight away. Practice answers never count in test results. |
| My progress | Score chart over time (tests and practice), skill trends, the skill to work on next, practice calendar and streak, best score per test |
| Mistakes notebook | Every correction and tip from tests and practice, grouped, with "I've learned this" ticks |
| Notifications | Bell in the top bar: teacher reviews and new tests (students), tests that need a review (admins) |

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
| `apps/evaluation/` | speech-to-text, scoring rules, written feedback, AI-written questions |
| `apps/learning/` | Quick practice, Mistakes notebook, My progress |
| `apps/notifications/` | in-app notifications (the bell), emails and endpoints for optional n8n automations |
| `apps/common/` | shared helpers and permissions |

The API is served under `/api/`; the frontend's `src/services/` folder shows every call it makes.
