# PARAKH — Deployment Guide

---

## Option A — Single Command (Local / Demo)

The recommended setup for hackathon demos and local development.

```bash
git clone https://github.com/YaduvanshiHimanshunfsu/PARAKH.git
cd PARAKH

# Configure
cp .env.example .env
# Edit .env — set OFFICER_USERNAME, OFFICER_PASSWORD, optionally GEMINI_API_KEY

# Launch (auto-installs venv + npm deps)
python run.py
```

| URL | Service |
|---|---|
| `http://localhost:5173` | Citizen Mode |
| `http://localhost:5173/officer` | Officer Console |
| `http://localhost:8000/docs` | API Swagger UI |

### Load demo data

```bash
.venv\Scripts\python -m app.db.seed          # Blacklists
.venv\Scripts\python -m app.db.demo_seed     # 14 cross-linked demo cases
.venv\Scripts\python -m app.db.units_seed    # Demo police units + 5 officers
```

---

## Option B — Vercel (Citizen Mode + API)

Best for the public-facing citizen endpoint. Investigation Mode requires a persistent host.

```bash
npm install -g vercel
vercel --prod
```

**Environment variables to set in Vercel dashboard:**

| Variable | Value |
|---|---|
| `GEMINI_API_KEY` | Your Google AI Studio key |
| `ENVIRONMENT` | `production` |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app` |
| `ENABLE_OFFLINE_FALLBACK` | `true` |
| `RATE_LIMIT_REQUESTS` | `20` |
| `DAILY_ANONYMOUS_LIMIT` | `120` |

> **Limitation:** Vercel serverless has an ephemeral filesystem. The SQLite database is recreated on every deployment. For Investigation Mode with persistent cases, use Option C.

---

## Option C — Persistent VPS / Railway / Render

For full dual-mode deployment including Investigation Mode.

```bash
# 1. Clone
git clone https://github.com/YaduvanshiHimanshunfsu/PARAKH.git
cd PARAKH

# 2. Create venv and install
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Set all variables — especially OFFICER_USERNAME, OFFICER_PASSWORD, DATABASE_URL

# 4. Build frontend
cd frontend && npm install && npm run build && cd ..

# 5. Seed
python -m app.db.seed
python -m app.db.demo_seed
python -m app.db.units_seed

# 6. Run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Option D — PostgreSQL (Production-Scale)

Change one line in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/parakh
```

No code changes required — SQLAlchemy handles the dialect.

---

## Environment Variables Reference

```env
# AI Provider (optional — offline rules work without this)
GEMINI_API_KEY=
GEMINI_MODEL_PREFERENCES=gemini-2.5-flash,gemini-2.0-flash,gemini-flash-latest
GEMINI_MAX_MODEL_ATTEMPTS=3

# Security
ALLOWED_ORIGINS=http://localhost:5173
ENVIRONMENT=development

# Rate limiting
RATE_LIMIT_REQUESTS=20
RATE_LIMIT_WINDOW_SECONDS=60
DAILY_ANONYMOUS_LIMIT=120

# Optional Redis rate limiting (for multi-instance production)
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=

# Database
DATABASE_URL=sqlite+aiosqlite:///./parakh_cases.db
DB_ECHO=false

# Officer account (required for Investigation Mode)
OFFICER_USERNAME=officer
OFFICER_PASSWORD=ChangeThisBeforeDemo123
AUTH_TOKEN_TTL_HOURS=12

# Upload limits
MAX_APK_UPLOAD_BYTES=60000000
MAX_REQUEST_BYTES=3250000
MAX_IMAGE_UPLOAD_BYTES=3000000

# URL intelligence
DOMAIN_AGE_ENABLED=true
DOMAIN_AGE_TIMEOUT_SECONDS=4
REDIRECT_FOLLOWING_ENABLED=true
MAX_REDIRECT_HOPS=5

# Optional enrichment (leave blank to use local heuristics only)
WEB_RISK_API_KEY=
VIRUSTOTAL_API_KEY=

# Optional error monitoring
SENTRY_DSN=
```
