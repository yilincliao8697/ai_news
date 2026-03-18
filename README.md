# AI News

An AI-powered news aggregator that fetches articles from a curated registry of RSS feeds, filters them for relevance using Claude, summarizes them into 2–4 sentence digests, and displays the results on a personal website — updated every 6 hours.

**Live site:** [ainews.yilincatherineliao.com](https://ainews.yilincatherineliao.com/)

---

## How it works

```
Feed Registry (DB)
       ↓
  fetch_articles()        ← feedparser, all enabled feeds
       ↓
  filter_article()        ← Claude: is this relevant?
       ↓
  summarize_article()     ← Claude: 2–4 sentence summary
       ↓
  save_article()          ← PostgreSQL via SQLAlchemy
       ↓
  FastAPI → Next.js       ← read-only public digest
```

The pipeline runs every 6 hours via APScheduler, embedded inside the FastAPI process. It can also be triggered manually from the `/admin` page.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| AI / LLM | Anthropic Claude (`claude-3-haiku-20240307`) |
| News ingestion | `feedparser` |
| ORM | SQLAlchemy |
| Database | PostgreSQL via Supabase |
| API | FastAPI + uvicorn |
| Scheduler | APScheduler (embedded in FastAPI, 6-hour interval) |
| Frontend | Next.js + Tailwind CSS |
| Backend hosting | Render / Railway / Fly.io |
| Frontend hosting | Vercel |

---

## Features

- **Digest view** — articles from the past 7 days grouped by date, with expandable 2–4 sentence summaries
- **Feed registry** — 173 RSS sources across research, industry, and science; up to 20 enabled at a time
- **Topic filtering** — All / Research / Industry tabs
- **Admin dashboard** — API key-gated feed management, pipeline trigger, error monitoring
- **Dark / light mode**

---

## Project Structure

```
ai-news/
├── ingestion/
│   └── fetcher.py              # RSS fetching and normalization
├── agents/
│   ├── filter_agent.py         # Relevance filter (Claude)
│   ├── summarize_agent.py      # Summarizer (Claude)
│   └── prompts/
│       ├── filter_prompt.txt
│       └── summarize_prompt.txt
├── database/
│   ├── models.py               # SQLAlchemy ORM models
│   └── crud.py                 # All DB read/write functions
├── api/
│   └── main.py                 # FastAPI — public + admin endpoints
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # Main page (Digest + Feed Registry tabs)
│   │   └── admin/
│   │       └── page.tsx        # Admin dashboard (key-gated)
│   └── components/
│       ├── FeedTable.tsx       # Feed list (interactive or read-only)
│       ├── DigestView.tsx      # Expandable article digest
│       └── ThemeToggle.tsx     # Dark/light mode toggle
├── scheduler/
│   └── pipeline.py             # Orchestrates full pipeline, runs every 6h
├── scripts/
│   └── import_feeds.py         # One-time feed registry seeder
├── tests/
│   ├── test_ingestion.py
│   ├── test_agents.py
│   ├── test_database.py
│   └── test_api.py
└── dataclasses_shared.py       # Shared data contracts
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)
- A PostgreSQL database (or use SQLite for local dev)

### 1. Clone and set up Python environment

```bash
git clone https://github.com/yilincliao8697/ai_news.git
cd ai_news

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```bash
ANTHROPIC_API_KEY=your_key_here
DATABASE_URL=sqlite:///./news.db          # or your PostgreSQL URL
ADMIN_API_KEY=your_secret_admin_key
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3. Seed the feed registry

```bash
python scripts/import_feeds.py
```

This populates the `feeds` table with 173 RSS sources. Safe to run multiple times.

### 4. Set up the frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Running Locally

**Terminal 1 — FastAPI backend** (includes scheduler)

```bash
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Next.js frontend**

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

To trigger the pipeline manually without waiting 6 hours:

```bash
source .venv/bin/activate
python -c "from scheduler.pipeline import run_pipeline; run_pipeline()"
```

---

## API Reference

Base URL: `http://localhost:8000`

### Public endpoints (no auth required)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/articles` | All articles, newest first. Query: `?topic=research\|industry\|science`, `?limit=N` |
| `GET` | `/admin/feeds` | All feeds with recent article previews |
| `GET` | `/scheduler/status` | Last run and next scheduled run times |

### Protected endpoints (require `X-Admin-Key` header)

| Method | Endpoint | Description |
|---|---|---|
| `PATCH` | `/admin/feeds/{id}` | Enable or disable a feed. Returns 409 if enabling would exceed 20-feed cap |
| `PATCH` | `/admin/feeds/bulk-toggle` | Enable/disable all feeds in a `source_type` group |
| `POST` | `/admin/feeds/{id}/reset-errors` | Reset `error_count` to 0 |
| `POST` | `/admin/run-pipeline` | Trigger full pipeline (blocking) |
| `POST` | `/feeds/{id}/fetch` | Queue a background pipeline run for one feed |

---

## Data Schema

```python
@dataclass
class Article:
    title: str
    link: str           # unique key
    source: str
    topic: str          # "research" | "industry" | "science"
    summary: str        # 2–4 sentence AI summary
    created_at: datetime
    published_at: datetime | None

@dataclass
class RawArticle:
    title: str
    link: str
    source: str
    topic: str
    content: str        # raw text (max 1000 chars), passed to agents
    published_at: datetime | None

@dataclass
class Feed:
    id: int
    name: str
    url: str            # unique key
    category: str       # "research" | "industry" | "science"
    enabled: bool
    last_fetched: datetime | None
    error_count: int
```

---

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

All Anthropic API calls are mocked — tests run without a real API key.

---

## Deployment

### Backend (Render / Railway / Fly.io)

Set environment variables:

```
ANTHROPIC_API_KEY=...
DATABASE_URL=postgresql://user:password@host:5432/dbname
ADMIN_API_KEY=your_secret_admin_key
```

Start command:

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

The scheduler starts automatically with the API process — no separate worker needed.

### Frontend (Vercel)

1. Import the repo into Vercel
2. Set **Root Directory** to `frontend/`
3. Add environment variable: `NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com`
4. Deploy

### Database (Supabase)

Set `DATABASE_URL` to your Supabase connection string. SQLAlchemy handles SQLite ↔ PostgreSQL automatically — no code changes required.

---

## Environment Variables

| Variable | Where | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | `.env` | Anthropic API key |
| `DATABASE_URL` | `.env` | SQLAlchemy DB URL. Default: `sqlite:///./news.db` |
| `ADMIN_API_KEY` | `.env` + hosting platform | Secret key for admin API endpoints |
| `NEXT_PUBLIC_API_BASE_URL` | `frontend/.env.local` + Vercel | Backend URL used by the browser |

---

## Acknowledgements

Feed sources seeded from [foorilla/allainews_sources](https://github.com/foorilla/allainews_sources) — a community-maintained list of AI, ML, and data newsletters and blogs.
