# WhatsApp Chat Analyzer

A production-style monorepo that analyzes exported WhatsApp `.txt` chats with a **Next.js** dashboard and a **FastAPI** API. Core parsing and analytics logic lives in `backend/preprocessor.py` and `backend/helper.py`.

## Architecture

```
WhatsApp-Chat-Analyzer/
├── backend/          # FastAPI + Python analytics (preprocessor, helper)
├── frontend/         # Next.js 15 + Recharts dashboard
└── docker-compose.yml
```

- **Backend:** Parses uploads once, caches sessions in memory (1 hour TTL), exposes JSON/chart data endpoints.
- **Frontend:** Upload flow, interactive dashboard, client-side charts via Recharts.

## Prerequisites

- Node.js 20+
- Python 3.11+

## Local development

### 1. Backend API

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements-api.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Run uvicorn from the `backend/` directory so `stop_hinglish.txt` resolves correctly.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chats` | Upload `.txt` export |
| GET | `/api/v1/chats/{id}/users` | User list |
| GET | `/api/v1/chats/{id}/stats?user=` | Message/word/media/link counts |
| GET | `/api/v1/chats/{id}/timeline/monthly` | Monthly timeline |
| GET | `/api/v1/chats/{id}/timeline/daily` | Daily timeline |
| GET | `/api/v1/chats/{id}/activity/week` | Busiest days |
| GET | `/api/v1/chats/{id}/activity/month` | Busiest months |
| GET | `/api/v1/chats/{id}/activity/heatmap` | Day × hour heatmap |
| GET | `/api/v1/chats/{id}/users/busy` | Top users (Overall only) |
| GET | `/api/v1/chats/{id}/words/common` | Top 20 words |
| GET | `/api/v1/chats/{id}/words/cloud` | Word cloud PNG |
| GET | `/api/v1/chats/{id}/emoji` | Emoji counts |
| GET | `/health` | Health check |

## Docker (full stack)

From the repository root:

```bash
docker compose up --build
```

- Frontend: [http://localhost:3000](http://localhost:3000)
- API: [http://localhost:8000](http://localhost:8000) · docs at `/docs`

`NEXT_PUBLIC_API_URL` is set at **build time** in `docker-compose.yml` (defaults to `http://localhost:8000` so the browser can reach the API on the host). Change the build arg if you deploy behind a public API URL.

Stop:

```bash
docker compose down
```

## Deployment

### Backend (Render / Railway / Fly)

- Root directory: `backend`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env: `CORS_ORIGINS=https://your-frontend.vercel.app`

Or use the included `Dockerfile` in `backend/`.

### Frontend (Vercel)

- Root directory: `frontend`
- Env: `NEXT_PUBLIC_API_URL=https://your-api.onrender.com`

## Privacy

Chat files are parsed in memory and stored in a temporary server session. Sessions expire after one hour (configurable via `SESSION_TTL_SECONDS`). No database persistence in v1.

## Features

- Message, word, media, and link statistics
- Monthly and daily timelines
- Week/month activity and heatmaps
- Group busy-user breakdown
- Word cloud and common words (Hinglish/English stopwords)
- Emoji table and distribution chart

