# Voice Mock Test System

A web app for practising spoken English with timed, exam-style speaking tests. Students record their answers in the browser and get a score for **fluency, pronunciation and grammar**, plus short written feedback. Teachers (admins) build the tests, review flagged answers and follow progress with reports.

![Landing page](docs/screenshots/landing.png)

**Live demo:** https://voice-mock-test-system.vercel.app (free hosting, so the first visit after a quiet period can take about a minute to wake up)

**Stack:** Django REST Framework · React 19 + Vite · PostgreSQL · Whisper speech-to-text · LLM feedback (Groq free tier or Claude) · Google sign-in

---

## Features

### For students
- **Speaking tests that feel like the real exam.** Each question has thinking time, then a timed recording. Students can listen back and re-record before submitting.
- **Microphone check** before every test, so a broken mic is caught before the first question.
- **Scores and feedback** for each answer and the whole test: fluency, pronunciation and grammar, what went well, one tip for next time and a next step.
- **Progress over time:** history of every test, average and best scores, strongest skill and the skill to focus on.
- **Pick up where you left off:** leaving a test keeps the saved answers, and the student continues at the next question.
- **Sign in with email or Google**, and reset a forgotten password by email.

### For teachers (admins)
- **Test builder:** create tests per level (beginner, intermediate, advanced), add and reorder questions with hints, set thinking and speaking time, allow or block retakes, and publish, unpublish or archive tests.
- **Review queue:** answers with low scores, very short answers, unclear audio or off-topic content are flagged automatically. The teacher can listen to the recording, read the transcript, adjust scores and feedback, re-score an answer and publish the review, with an optional email to the student.
- **Dashboard:** active students, tests taken this week compared with last week, average score and skills this week.
- **Reports:** filter by date, test and level; see skill averages, score ranges, tests per day and results by test, and download everything as a CSV file for Excel.
- **People management:** invite students or admins by email link, change levels, suspend accounts and search or sort by score.

### Under the hood
- JWT authentication with refresh-token rotation and sign-out (token blacklist).
- Role-based access: students only ever see their own data.
- Request limits on sign-in, sign-up and password reset.
- One-time links for invitations and password resets, stored only as SHA-256 hashes.
- **Demo mode:** the whole app works without any API keys by using sample scores.
- Recordings stored locally or in S3-compatible storage (for example Supabase Storage).
- Optional API endpoints for n8n automations (pending-review alerts, weekly summary email).
- 92 automated backend tests, run on SQLite and PostgreSQL.

---

## How scoring works

```mermaid
flowchart LR
    A[Recording in the browser] --> B[Django API]
    B --> C[Speech-to-text<br/>Whisper on Groq or OpenAI]
    C --> D[Delivery measurements<br/>pace, filler words,<br/>pauses, clarity]
    D --> E[Written feedback<br/>gpt-oss on Groq or Claude]
    E --> F[Scores and feedback<br/>for the student]
    F -- low score, short answer,<br/>unclear audio, off topic --> G[Teacher review queue]
```

- **Overall score** = 40% fluency + 30% pronunciation + 30% grammar. The weights can be changed in `backend/.env`.
- **Flagged for review:** an answer is sent to the review queue when its score is under 65%, it's very short, the audio is hard to hear, or it may be off topic.
- **Free scoring:** with `AI_PROVIDER=groq`, one free Groq key runs both steps (Whisper speech-to-text and the open gpt-oss model for feedback).
- **Paid scoring:** with `AI_PROVIDER=openai`, OpenAI speech-to-text and Anthropic Claude feedback.
- **Demo mode** (`EVALUATION_DEMO_MODE=True`) skips the AI calls and returns sample scores, so the app can be run and shown without any keys.

---

## Screenshots

> Screenshots use sample students and demo-mode scores.

### Student

| Dashboard | Speaking test |
|---|---|
| ![Student dashboard](docs/screenshots/student-dashboard.png) | ![Speaking test](docs/screenshots/speaking-test.png) |
| **Results** | **History** |
| ![Results](docs/screenshots/results.png) | ![History](docs/screenshots/history.png) |

### Admin

| Dashboard | Review an answer |
|---|---|
| ![Admin dashboard](docs/screenshots/admin-dashboard.png) | ![Review](docs/screenshots/review.png) |
| **Reports** | **Students** |
| ![Reports](docs/screenshots/reports.png) | ![Students](docs/screenshots/students.png) |
| **Mock tests** | **Question editor** |
| ![Mock tests](docs/screenshots/tests.png) | ![Questions](docs/screenshots/questions.png) |

### Phone

Every page works on phones, with a slide-out menu.

![Phone screens](docs/screenshots/mobile.png)

---

## Tech stack

| Part | Technology |
|---|---|
| Backend | Python, Django 5.2, Django REST Framework, Simple JWT, django-cors-headers, django-environ |
| Database | PostgreSQL (local or Supabase); SQLite for quick local runs |
| Frontend | React 19, Vite 8, React Router 7, Axios, Lucide icons, plain CSS with design tokens |
| Speech-to-text | Whisper: `whisper-large-v3-turbo` on Groq (free) or OpenAI `whisper-1` |
| Feedback | `openai/gpt-oss-120b` on Groq (free) or Anthropic Claude `claude-haiku-5-5` |
| Sign-in | Email and password, Google Identity Services |
| Storage | Local `media/` folder or S3-compatible storage (django-storages) |
| Email | Django SMTP (for example Gmail) or n8n webhooks |
| Hosting | Vercel (website), Render (API), Supabase (PostgreSQL database and recording storage) |

---

## Run it locally

You need **Python 3.11+** and **Node.js 20.19+**. PostgreSQL is optional: without it, the app uses an SQLite file.

**1. Backend** (first terminal):

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux
pip install -r requirements.txt
copy .env.example .env              # macOS / Linux: cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

**2. Frontend** (second terminal):

```bash
cd frontend
npm install
npm run dev
```

**3.** Open **http://localhost:5173**.

| Account | Email | Password |
|---|---|---|
| Admin (created by `migrate`) | admin@example.com | admin123 (change it after the first sign-in) |
| Demo student (created by `seed_demo`) | student@example.com | student123 |

More detail:
- [`backend/README.md`](backend/README.md): connecting PostgreSQL or Supabase, Google sign-in, real scoring, email.
- [`frontend/README.md`](frontend/README.md): building and hosting the website.

### Main settings (`backend/.env`)

| Setting | What it does |
|---|---|
| `DATABASE_URL` | Empty = SQLite. Otherwise `postgres://user:password@host:port/database` |
| `GOOGLE_CLIENT_ID` | Turns on the Google sign-in button |
| `EVALUATION_DEMO_MODE` | `True` = sample scores; `False` = real scoring |
| `AI_PROVIDER`, `GROQ_API_KEY` | `groq` + a free Groq key for real scoring |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | For `AI_PROVIDER=openai` (paid) instead |
| `EMAIL_BACKEND`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Real email for invitations, password resets and reviews |
| `REVIEW_THRESHOLD`, `SCORE_WEIGHT_*` | When answers are flagged and how the overall score is weighted |

### Tests

```bash
cd backend
python manage.py test
```

---

## Project structure

```
voice-mock-test-system/
├── backend/                 Django REST API
│   ├── config/              settings and URLs
│   └── apps/
│       ├── accounts/        users, roles, sign-in, Google sign-in, invitations, password reset
│       ├── tests_manager/   mock tests and questions
│       ├── attempts/        taking tests, answers, results, reviews, dashboard, reports
│       ├── evaluation/      speech-to-text, scoring rules, written feedback (Groq or OpenAI + Claude)
│       ├── notifications/   emails and n8n endpoints
│       └── common/          shared helpers and permissions
└── frontend/                React website
    └── src/
        ├── pages/           student, admin and public pages
        ├── components/      buttons, fields, recorder, dialogs, score ring…
        ├── layouts/         page frames (sidebar + top bar)
        ├── services/        API calls with automatic token refresh
        ├── hooks/           microphone recording
        └── styles/          design tokens and styles
```

## API overview

All endpoints are under `/api/`.

| Area | Endpoints |
|---|---|
| Auth | `auth/register/`, `auth/login/`, `auth/google/`, `auth/refresh/`, `auth/logout/`, `auth/me/`, `auth/password-reset/` |
| Student | `tests/`, `attempts/`, `attempts/{id}/answers/`, `attempts/{id}/submit/`, `me/stats/` |
| Admin | `admin/users/`, `admin/users/invite/`, `admin/tests/`, `admin/questions/`, `admin/attempts/`, `admin/attempts/{id}/review/`, `admin/dashboard/`, `admin/reports/`, `admin/reports/export/` |
| Scoring | `evaluation/config/`, `evaluation/answers/{id}/rescore/` |

---

Built by **Roshan Rawal**.
