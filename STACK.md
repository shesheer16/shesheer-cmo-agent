# STACK.md — Complete Technology Stack
## Shesheer CMO Agent — Zero Cost Architecture

---

## Stack Philosophy

**Rule 1:** Every tool must cost ₹0 unless there is no free alternative
**Rule 2:** Every tool must be production-grade, not a toy
**Rule 3:** Every tool must be replaceable without breaking the system
**Rule 4:** The only paid component is Gemini API — the intelligence brain

---

## Complete Stack Decision Table

### Core Language & Runtime

| Component | Choice | Alternative | Why This |
|---|---|---|---|
| Language | Python 3.11+ | Node.js | Best AI/ML ecosystem, all libraries native |
| Package Manager | uv (Astral) | pip/poetry | 10-100x faster than pip, zero cost |
| Virtual Env | uv venv | conda | Lightweight, fast, standard |
| Runtime Config | python-dotenv | hardcoded | Environment variable management |

---

### Intelligence Layer (The Brain)

| Component | Choice | Alternative | Why This |
|---|---|---|---|
| Primary LLM | Gemini 2.5 Flash  | GPT-4o | Best reasoning for complex Indian market analysis |
| Premium LLM | Gemini 2.5 Pro  | GPT-4-turbo | For deep strategic synthesis (use sparingly) |
| LLM Framework | Google GenAI SDK (direct) | LangChain | Direct API = faster, fewer abstractions, cheaper |
| Prompt Management | Plain Python + Jinja2 | LangChain prompts | Full control, zero framework overhead |

**Cost Control:**
```
Gemini 2.5 Flash:  Use for daily conversations (90% of calls)
Gemini 2.5 Pro:    Use only for weekly deep strategy sessions (10%)
Max tokens:  1,500 per response (sufficient for strategic memos)
Daily budget: ~₹50-150 per day at normal usage
```

---

### Vector Database (The Memory of Knowledge)

| Component | Choice | Alternative | Why This |
|---|---|---|---|
| Vector DB | ChromaDB | Pinecone, Qdrant | 100% local, zero cost, Python-native |
| Persistence | ChromaDB PersistentClient | In-memory | Data survives restarts |
| Collections | Separate per domain | Single collection | Cleaner retrieval per knowledge domain |

**ChromaDB Collections Architecture:**
```
collection: founders_mindsets
collection: campaign_case_studies
collection: market_data_reports
collection: cmo_profiles
collection: consumer_psychology
collection: books_annotations
collection: social_media_intelligence
collection: startup_context (your personal data)
```

---

### Embedding Model (Converts Text to Vectors)

| Component | Choice | Alternative | Why This |
|---|---|---|---|
| Embedding Model | sentence-transformers/all-MiniLM-L6-v2 | OpenAI text-embedding-3 | 100% local, zero cost, 384 dimensions |
| Premium Embedding | intfloat/multilingual-e5-large | Cohere Embed | Handles Hindi/Hinglish content |
| Embedding Runner | sentence-transformers library | Hugging Face Inference API | Local = zero latency + zero cost |

**Why two embedding models:**
```
all-MiniLM-L6-v2      → English content (fast, lightweight)
multilingual-e5-large  → Hindi/Hinglish/regional content (accurate)
```

---

### Data Ingestion Pipeline

| Component | Choice | Alternative | Why This |
|---|---|---|---|
| Web Scraping | BeautifulSoup4 + httpx | Firecrawl ($16/mo) | Free, sufficient for curated scraping |
| YouTube Transcripts | yt-dlp + youtube-transcript-api | Whisper API ($) | Completely free YouTube transcript extraction |
| Audio Transcription | faster-whisper (local) | OpenAI Whisper API | Local model, zero cost, sufficient accuracy |
| PDF Processing | pypdf2 + pdfplumber | Adobe API | Free, handles most PDF formats |
| LinkedIn Scraping | manual export + linkedin-api | Phantom Buster ($) | Manual curation = higher quality anyway |
| Document Processing | markdownify | custom parser | Converts HTML to clean markdown |
| Rate Limiting | tenacity (retry library) | custom | Prevents scraping blocks |

---

### Backend API

| Component | Choice | Alternative | Why This |
|---|---|---|---|
| API Framework | FastAPI | Flask, Django | Async, fast, auto-docs, Python-native |
| ASGI Server | uvicorn | gunicorn | Lightweight, production-ready |
| Task Queue | APScheduler | Celery + Redis | Zero infrastructure overhead |
| Data Validation | Pydantic v2 | marshmallow | Native FastAPI integration |
| HTTP Client | httpx | requests | Async support, modern |

---

### Memory & Storage Layer

| Component | Choice | Alternative | Why This |
|---|---|---|---|
| Primary DB | SQLite | PostgreSQL | Zero infrastructure, file-based, sufficient |
| ORM | SQLAlchemy 2.0 | raw SQL | Type safety, migrations |
| Migrations | Alembic | manual | Version-controlled schema |
| Cache | diskcache | Redis | Zero infrastructure, file-based |
| Session Store | SQLite JSON columns | Redis | Keeps infrastructure minimal |

**SQLite Database Schema Overview:**
```
tables:
  startup_context      → Your startup's live state
  conversations        → Full conversation history
  decisions_log        → Every decision you consulted agent for
  pivots_log           → Pivots suggested and taken
  knowledge_sources    → Ingested source registry
  annotations          → Manual case study annotations
```

---

### Interface Layer

| Component | Choice | Alternative | Why This |
|---|---|---|---|
| Primary Interface | Telegram Bot (python-telegram-bot) | WhatsApp Twilio ($) | Free forever, voice notes, fast |
| Secondary Interface | Streamlit | Next.js, React | Zero frontend code needed |
| Voice Processing | faster-whisper | OpenAI Whisper API | Local transcription, free |
| WhatsApp (future) | Meta Cloud API | Twilio | Free tier exists, direct integration |

**Why Telegram over WhatsApp for MVP:**
```
WhatsApp Business API → Requires Twilio = ₹2,000+/month
Meta Cloud API        → Complex setup, approval process
Telegram Bot API      → Free forever, instant setup,
                        voice notes work perfectly,
                        same daily-use behavior
Migrate to WhatsApp   → Phase 9 after validation
```

---

### Development Environment

| Component | Choice | Why This |
|---|---|---|
| Primary IDE | Google Antigravity 2.0 | Agent-first, multi-agent parallel build |
| Fallback IDE | VS Code + Continue.dev | When Antigravity agents need guidance |
| Version Control | Git + GitHub | Standard |
| API Testing | httpie + Bruno | Free Postman alternatives |
| Secrets Management | .env + python-dotenv | Simple, standard |
| Linting | ruff | 100x faster than pylint, zero config |
| Type Checking | mypy | Catches bugs before runtime |

---

### Deployment (Free Tier)

| Component | Choice | Alternative | Why This |
|---|---|---|---|
| Hosting | Railway (free tier) | Render, Fly.io | 512MB RAM, always-on, generous free tier |
| Database | SQLite file on Railway volume | PlanetScale free | Simplest possible persistence |
| Vector DB | ChromaDB on Railway | Pinecone free | Same local instance, deployed |
| Telegram Bot | Railway always-on | Heroku | Free tier sufficient |
| Streamlit UI | Streamlit Cloud (free) | Vercel | Zero DevOps |
| Domain | Freenom or subdomain | Custom domain | Not needed for personal tool |

---

### Monitoring & Observability (Free)

| Component | Choice | Why This |
|---|---|---|
| Logging | Python logging + loguru | Rich, colored, structured logs |
| Cost Tracking | Custom SQLite table | Logs every Gemini API call + cost |
| Error Tracking | Sentry (free tier) | 5,000 errors/month free |
| Uptime | Better Uptime (free) | Pings your endpoint every 3 minutes |

---

## The Complete Dependency File

```toml
# pyproject.toml

[project]
name = "shesheer-cmo-agent"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # Intelligence
    "google-genai>=0.30.0",

    # Vector Database
    "chromadb>=0.5.0",

    # Embeddings (local, free)
    "sentence-transformers>=3.0.0",

    # Audio Transcription (local, free)
    "faster-whisper>=1.0.0",

    # YouTube & Web Ingestion
    "yt-dlp>=2024.1.0",
    "youtube-transcript-api>=0.6.0",
    "beautifulsoup4>=4.12.0",
    "httpx>=0.27.0",
    "markdownify>=0.12.0",

    # PDF Processing
    "pypdf2>=3.0.0",
    "pdfplumber>=0.11.0",

    # Backend
    "fastapi>=0.111.0",
    "uvicorn>=0.30.0",
    "python-telegram-bot>=21.0",
    "streamlit>=1.36.0",

    # Database & Storage
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "diskcache>=5.6.0",

    # Data & Validation
    "pydantic>=2.7.0",
    "python-dotenv>=1.0.0",
    "jinja2>=3.1.0",

    # Utilities
    "tenacity>=8.4.0",
    "loguru>=0.7.0",
    "ruff>=0.4.0",
    "apscheduler>=3.10.0",
]
```

---

## Environment Variables Required

```env
# .env (never commit this file)

# Intelligence Layer
GEMINI_API_KEY=your_key_here
DEFAULT_MODEL=claude-sonnet-4-6
PREMIUM_MODEL=claude-opus-4-6
MAX_TOKENS=1500
TEMPERATURE=0.3

# Telegram Interface
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_ALLOWED_USER_ID=your_telegram_id

# Storage Paths
CHROMA_DB_PATH=./data/chromadb
SQLITE_DB_PATH=./data/shesheer_cmo.db
KNOWLEDGE_BASE_PATH=./data/knowledge_base
AUDIO_CACHE_PATH=./data/audio_cache

# Ingestion Controls
MAX_CONCURRENT_SCRAPERS=3
SCRAPE_DELAY_SECONDS=2
WHISPER_MODEL=base  # base=free fast, large=slower accurate

# Feature Flags
CHALLENGER_MODE=true
MEMORY_ENABLED=true
COST_TRACKING=true
DEBUG_MODE=false
```

---

## Cost Calculation — Real Numbers

```
SCENARIO 1: Light use (10 conversations/day)
Gemini 2.5 Flash input:  ~500 tokens × 10 = 5,000 tokens/day
Gemini 2.5 Flash output: ~1,500 tokens × 10 = 15,000 tokens/day
Monthly:              600,000 tokens total
Cost at Sonnet rates: ~₹800-1,200/month

SCENARIO 2: Heavy use (25 conversations/day)
Monthly tokens:       ~1.5M tokens
Cost at Sonnet rates: ~₹2,000-3,500/month

SCENARIO 3: Premium sessions (5 Opus calls/week)
Additional Opus cost: ~₹500-800/month

REALISTIC TOTAL:      ₹1,500-4,000/month
Everything else:      ₹0
```

---

## What This Stack Enables

```
Day 1:  Environment running, ChromaDB initialized
Day 3:  First 10 case studies ingested and queryable
Day 5:  System prompt live, first CMO conversation
Day 7:  Telegram bot deployed, daily use begins
Day 14: Full ingestion pipeline running
Day 21: Memory layer compound intelligence begins
Day 30: First strategic decision changed by the agent
```

---

*Stack designed for: zero operational overhead, maximum intelligence,
Indian founder budget constraints, production-grade architecture.*