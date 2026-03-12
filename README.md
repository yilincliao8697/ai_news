# AI News Aggregator

An AI-powered news aggregation system that fetches articles from RSS feeds, filters them for relevance using Claude, summarizes them into 2–4 sentence digests, and displays the results on a personal website.

## How it works

```
RSS Feeds → Filter Agent → Summarize Agent → SQLite DB → FastAPI → Next.js
```

1. **Ingestion** — `feedparser` pulls articles from 3 RSS feeds every 6 hours
2. **Filter** — Claude decides if each article is relevant to its topic (ai / tech / science)
3. **Summarize** — Claude writes a 2–4 sentence plain-English summary
4. **Store** — SQLAlchemy writes to SQLite (upgradeable to PostgreSQL)
5. **API** — FastAPI serves read-only JSON endpoints
6. **Frontend** — Next.js + Tailwind displays the curated feed

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| AI / LLM | Anthropic Claude (`claude-3-haiku-20240307`) |
| News ingestion | `feedparser` |
| ORM | SQLAlchemy |
| Database | SQLite (MVP) → PostgreSQL (production) |
| API | FastAPI + uvicorn |
| Frontend | Next.js 16 + Tailwind CSS |
| Scheduler | APScheduler (BlockingScheduler, 6-hour interval) |
| Backend hosting | Render / Railway / Fly.io |
| Frontend hosting | Vercel |

---

## Project Structure

```
ai-news/
├── ingestion/
│   └── fetcher.py           # RSS fetching and normalization
├── agents/
│   ├── filter_agent.py      # Relevance filter (Claude)
│   ├── summarize_agent.py   # Summarizer (Claude)
│   └── prompts/
│       ├── filter_prompt.txt
│       └── summarize_prompt.txt
├── database/
│   ├── models.py            # SQLAlchemy ORM model
│   └── crud.py              # save_article, get_articles, get_articles_by_topic
├── api/
│   └── main.py              # FastAPI — GET /articles, GET /health
├── frontend/                # Next.js app (App Router + Tailwind)
│   ├── app/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   └── components/
│       ├── ArticleCard.tsx
│       └── TopicFilter.tsx
├── scheduler/
│   └── pipeline.py          # Orchestrates full pipeline, runs every 6h
├── tests/
│   ├── test_ingestion.py
│   ├── test_agents.py
│   ├── test_database.py
│   └── test_api.py
├── dataclasses_shared.py    # Shared data contracts (Article, RawArticle, etc.)
├── requirements.txt
└── CLAUDE.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)

### 1. Clone and set up Python environment

```bash
git clone <your-repo-url>
cd ai-news

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env             # or create .env manually
```

Edit `.env`:

```bash
ANTHROPIC_API_KEY=your_key_here
DATABASE_URL=sqlite:///./news.db
API_BASE_URL=http://localhost:8000
```

### 3. Set up the frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local  # or create manually
```

Edit `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Running Locally

Open three terminals:

**Terminal 1 — FastAPI backend**

```bash
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Run the pipeline once** (to populate the database)

```bash
source .venv/bin/activate
python -c "from scheduler.pipeline import run_pipeline; run_pipeline()"
```

Or start the full scheduler (runs immediately, then every 6 hours):

```bash
python scheduler/pipeline.py
```

**Terminal 3 — Next.js frontend**

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## API Reference

Base URL: `http://localhost:8000`

### `GET /health`

Liveness check.

```json
{"status": "ok"}
```

### `GET /articles`

Returns all articles, newest first.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `topic` | string | — | Filter by topic: `ai`, `tech`, or `science` |
| `limit` | integer | 100 | Max results (1–500) |

**Example:**

```bash
curl "http://localhost:8000/articles?topic=ai&limit=10"
```

**Response:**

```json
[
  {
    "title": "New LLM Benchmark Released",
    "link": "https://example.com/article",
    "source": "Latent Space",
    "topic": "ai",
    "summary": "Researchers released a new benchmark for evaluating LLM reasoning. The benchmark tests multi-step logic across 5,000 problems. Initial results show Claude and GPT-4 performing competitively.",
    "created_at": "2026-03-11T10:00:00"
  }
]
```

**Error (invalid topic):**

```json
{"error": "Invalid topic 'sports'. Must be one of: ['ai', 'science', 'tech']"}
```

---

## RSS Feeds

| Topic | Feed |
|---|---|
| `ai` | Latent Space — `www.latent.space/feed` |
| `tech` | Ars Technica — `feeds.arstechnica.com/arstechnica/index` |
| `science` | Science Daily — `sciencedaily.com/rss/top/science.xml` |

---

## Data Schema

All modules share these dataclasses from `dataclasses_shared.py`:

```python
@dataclass
class Article:
    title: str
    link: str        # unique key
    source: str
    topic: str       # "ai" | "tech" | "science"
    summary: str     # 2–4 sentence AI summary
    created_at: datetime

@dataclass
class RawArticle:
    title: str
    link: str
    source: str
    topic: str
    content: str     # raw text (max 1000 chars), passed to agents

@dataclass
class FilterResult:
    is_relevant: bool
    reason: str

@dataclass
class SummaryResult:
    summary: str
```

---

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

Expected output:

```
tests/test_agents.py .....       5 passed
tests/test_api.py .......        7 passed
tests/test_database.py .....     5 passed
tests/test_ingestion.py ........  8 passed

25 passed
```

All Anthropic API calls are mocked — tests run without a real API key.

---

## Module Boundaries

Each module has a strictly enforced single responsibility:

| Module | Reads from | Writes to | Calls AI |
|---|---|---|---|
| `ingestion/` | RSS feeds | — | No |
| `agents/` | `RawArticle` input | — | Yes |
| `database/` | DB | DB | No |
| `api/` | DB (read-only) | — | No |
| `scheduler/` | All modules | via `database/` | via `agents/` |
| `frontend/` | API only | — | No |

---

## Deployment

### Backend (Render / Railway / Fly.io)

1. Set environment variables: `ANTHROPIC_API_KEY`, `DATABASE_URL`, `API_BASE_URL`
2. Start command:
   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port $PORT
   ```
3. For the scheduler, run as a separate worker process:
   ```bash
   python scheduler/pipeline.py
   ```

### Frontend (Vercel)

1. Import the repo into Vercel
2. Set **Root Directory** to `frontend/`
3. Add environment variable:
   ```
   NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com
   ```
4. Deploy

### Database upgrade (SQLite → PostgreSQL)

No code changes required. Just update `DATABASE_URL` in your environment:

```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

SQLAlchemy handles the rest.

---

## Environment Variables Reference

| Variable | Where | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | `.env` | Anthropic API key |
| `DATABASE_URL` | `.env` | SQLAlchemy DB URL. Default: `sqlite:///./news.db` |
| `API_BASE_URL` | `.env` | Backend URL used internally. Default: `http://localhost:8000` |
| `NEXT_PUBLIC_API_BASE_URL` | `frontend/.env.local` | Backend URL used by the browser |
