# 🎓 Smart Tutor - AI-Powered Video Learning

An audio-first AI tutor that lets you paste a YouTube video, watch it, pause at any point, and ask questions that are answered with full awareness of what's being discussed at that moment.

## Architecture

```
frontend/          → Next.js + TypeScript + Tailwind CSS
backend/           → Python + FastAPI
Database           → Supabase (PostgreSQL + Auth)
AI                 → OpenAI GPT-4o-mini (answering) + Whisper (fallback transcription)
Transcription      → YouTube captions (primary, free) + Whisper API (fallback)
Hosting            → Railway (backend + frontend)
```

## Local Development

### Prerequisites
- Python 3.9+
- Node.js 18+
- ffmpeg (`brew install ffmpeg` on macOS)
- Supabase project (free tier)
- OpenAI API key

### 1. Database Setup

Run `backend/schema.sql` in your Supabase Dashboard → SQL Editor → New Query.

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Edit with your real keys
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
# Create .env.local with:
#   NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
#   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
#   NEXT_PUBLIC_API_URL=http://localhost:8000/api
npm run dev
```

### 4. Open the App

Go to http://localhost:3000

---

## Railway Deployment

### Step 1: Create a GitHub Repo

```bash
git init
git add .
git commit -m "Initial commit: Smart Tutor app"
git remote add origin https://github.com/YOUR_USERNAME/Education_App.git
git push -u origin main
```

### Step 2: Deploy on Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub Repo**
2. Select your repo
3. Railway will auto-detect the monorepo. Create **two services**:

#### Service 1: Backend (API)
- **Root Directory**: `backend`
- **Environment Variables** (add in Railway dashboard):
  ```
  SUPABASE_URL=https://xxx.supabase.co
  SUPABASE_ANON_KEY=your-anon-key
  SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
  OPENAI_API_KEY=sk-proj-xxx
  CORS_ORIGINS=https://your-frontend.up.railway.app
  PORT=8000
  ```
- Railway will auto-detect `requirements.txt` and `railway.toml`
- Generates a public URL like `https://your-backend.up.railway.app`

#### Service 2: Frontend (Next.js)
- **Root Directory**: `frontend`
- **Environment Variables** (add in Railway dashboard):
  ```
  NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
  NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
  NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app/api
  PORT=3000
  ```
- Generates a public URL like `https://your-frontend.up.railway.app`

### Step 3: Update CORS

After both services are deployed, update the **backend** `CORS_ORIGINS` env var to include the frontend's Railway URL.

### Step 4: Supabase Auth Redirect

In Supabase Dashboard → Authentication → URL Configuration:
- **Site URL**: `https://your-frontend.up.railway.app`
- **Redirect URLs**: Add `https://your-frontend.up.railway.app/**`

---

## How It Works

1. **Sign up / Log in** via email or Google
2. **Paste a YouTube URL** → the app extracts the transcript
3. **Watch the video** → the transcript scrolls along
4. **Pause and ask a question** → the AI answers using the transcript context around that moment
5. **Your Q&A history is saved** and used for future context

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/videos/` | Submit a YouTube URL |
| GET | `/api/videos/{id}` | Get video details |
| GET | `/api/videos/{id}/status` | Poll processing status |
| GET | `/api/transcripts/{id}` | Get full transcript |
| GET | `/api/transcripts/{id}/window` | Get transcript around a timestamp |
| POST | `/api/qa/ask` | Ask a question (non-streaming) |
| POST | `/api/qa/ask/stream` | Ask a question (SSE streaming) |
| GET | `/api/qa/history/{video_id}` | Get Q&A history |

## Cost

- ~$0.0004 per question (GPT-4o-mini)
- ~$0.006/min for Whisper (only when YouTube captions unavailable)
- Hosting: ~$8-15/month for 100 active users
