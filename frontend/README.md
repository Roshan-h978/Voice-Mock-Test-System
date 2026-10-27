# Voice Mock Test - frontend (React + Vite)

## Run it

Needs Node.js 20.19+ (22 or 24 recommended). Start the backend first, then open a **second** PowerShell window **in this `frontend` folder**:

```
npm install
npm run dev
```

Open **http://localhost:5173** and sign in with **admin@example.com / admin123** (or create a student account).

Next time you only need `npm run dev`.

## How it talks to the backend

During development the app calls `/api/...` and Vite forwards it to Django at `http://127.0.0.1:8000` (set in `vite.config.js`). No other setup is needed.
To use a different backend address, copy `.env.example` to `.env` and change `VITE_BACKEND_URL`.

The Google button reads its client ID from the backend (`GOOGLE_CLIENT_ID` in `backend/.env`), so there is nothing to set here.

## Build for hosting

```
npm run build
```

Upload the `dist` folder to any static host (Netlify, Vercel, Cloudflare Pages…). Before building, set `VITE_API_URL=https://your-backend-address/api` in `.env`, and add a rule that sends every path to `/index.html`.

## Folder guide

| Folder | What's inside |
| --- | --- |
| `src/pages/common` | Home, sign-in, sign-up, forgot / reset password |
| `src/pages/student` | Dashboard, test instructions, speaking test, results, history, profile |
| `src/pages/admin` | Dashboard, students, tests, questions, reviews, reports |
| `src/components` | Shared pieces: buttons, fields, recorder, Google button, sidebar, dialogs, score ring… |
| `src/layouts` | Student and admin page frames (sidebar + top bar) |
| `src/services` | Every API call (axios, automatic token refresh) |
| `src/hooks` | `useAudioRecorder` (microphone recording) |
| `src/context` | Signed-in user |
| `src/styles` | Design tokens (`variables.css`) and all styles (`global.css`) |

Recording needs a current browser and either `http://localhost` or `https://`. Allow the microphone when the browser asks.
