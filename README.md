# PARAKH — परख

> **परखो, फिर भरोसो | Test Before You Trust**

**Rajasthan Police Hackathon 2026 — Problem Statement PS01**
*Scam Message & Phishing Link Detection with Fake Loan / Investment App and Fraudulent Website Analysis*

---

## What is PARAKH?

*Parakh* (परख) means *the touchstone test* — the gold-purity test a jeweler uses before accepting a piece. PARAKH applies that same rigour to digital fraud: every suspicious message, URL, APK or website is tested on the touchstone before you trust it.

PARAKH is a **dual-mode** investigation and citizen-safety platform:

| Mode | Who uses it | What it stores |
|---|---|---|
| **Citizen Mode** | Public-facing — anyone can submit a suspicious message or link | Nothing. Fully ephemeral. |
| **Investigation Mode** | Rajasthan Police officers (bearer-token gated) | All analyses, with full case history, linking and export |

---

## PS01 Compliance

| Requirement | How PARAKH addresses it |
|---|---|
| Analyse a message or URL, return risk level + reasons | `POST /api/v1/parakh/analyze`, `POST /api/v1/parakh/url/analyze` — Low / Medium / High with per-finding explanations |
| Analyse at least one APK **or** one website and extract identifiers | APK static analysis (permissions, manifest, signing cert, dHash) **and** website analysis (guarded fetch, identifier harvesting) — both implemented |
| Extract URLs, phone numbers, UPI IDs from artifacts | 14 identifier types: UPI, phone, URL, domain, IP, email, bank account, Telegram, WhatsApp, crypto wallet, certificate fingerprint, package name, app label, QR payload |
| Dashboard with case history, search, downloadable report | Officer console at `/investigate` — paginated search, identifier linking, heat-list, JSON/HTML/CSV export |
| Identifier linking across messages, apps, websites | `GET /api/v1/investigate/identifier/{value}/cases` — weighted linking by identifier type |
| Heat-list of trending scam domains and numbers | `GET /api/v1/investigate/heat-list` |

---

## Architecture

```
Browser
  ├── Citizen SPA  (React 19 + Tailwind v4)
  │     └──  POST /api/v1/parakh/*          ← ephemeral, no auth
  └── Officer SPA  (same build, /investigate routes)
        └──  POST/GET /api/v1/investigate/* ← bearer-token gated

FastAPI backend
  ├── ScamAnalyzer      — rule engine + Gemini (deterministic fallback)
  ├── ArtifactAnalyzer  — message / URL / email
  ├── ApkAnalyzer       — static APK inspection (pyaxmlparser, asn1crypto)
  ├── WebsiteAnalyzer   — guarded fetch, identifier harvest
  ├── IdentifierExtractor — 14 types, span-based overlap resolution
  ├── CaseService       — create / search / link / export
  └── LinkService       — identifier linking, similarity (SimHash), heat-list

SQLite (aiosqlite + SQLAlchemy 2 async)
  └── users · cases · findings · identifiers · blacklist · domain_intel
```

---

## Quick Start

### Option A — Full stack (recommended for the demo)

```bash
# 1. Backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

cp .env.example .env
# Edit .env: set OFFICER_USERNAME and OFFICER_PASSWORD

python -m app.db.seed          # seed blacklist
python -m app.db.demo_seed     # 14 demo cases (10 SMS, 2 websites, 2 APKs)
uvicorn app.main:app --reload

# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev
# → http://localhost:5173  (citizen)
# → http://localhost:5173/investigate  (officer console)
```

### Option B — Backend only (API + Swagger UI)

```bash
uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

---

## Officer Console

Navigate to `/investigate/login`. Default credentials are set in `.env` (`OFFICER_USERNAME` / `OFFICER_PASSWORD`).

**Change the password before any public demo.** The default value in `.env` is intentionally weak and must be replaced.

### Investigation API

All routes require `Authorization: Bearer <token>` obtained from `POST /api/v1/investigate/login`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/investigate/login` | Officer sign-in → bearer token |
| GET | `/investigate/health` | Liveness check |
| POST | `/investigate/submit` | Analyse message / URL / email and persist as a case |
| POST | `/investigate/apk/analyze` | Static APK analysis (upload) |
| POST | `/investigate/website/analyze` | Guarded website fetch and analysis |
| GET | `/investigate/cases` | Paginated case list (search, filter) |
| GET | `/investigate/cases/{id}` | Full case detail |
| PATCH | `/investigate/cases/{id}/status` | Update status + officer note |
| DELETE | `/investigate/cases/{id}` | Soft delete |
| GET | `/investigate/identifier/{value}/cases` | All cases sharing an identifier |
| GET | `/investigate/cases/{id}/linked` | Cases linked by shared identifiers |
| GET | `/investigate/cases/{id}/similar` | Cases with near-duplicate content (SimHash) |
| GET | `/investigate/heat-list` | Most-seen identifiers across all cases |
| GET | `/investigate/export/cases.json` | Bulk JSON export (filtered) |
| GET | `/investigate/export/cases.csv` | Bulk CSV export (filtered) |
| GET | `/investigate/export/identifiers.csv` | Identifier dump |
| GET | `/investigate/cases/{id}/report.json` | Per-case JSON report |
| GET | `/investigate/cases/{id}/report.html` | Per-case print-ready HTML report |
| POST | `/investigate/url/precheck` | Fast blacklist + TLS check (no case created) |

---

## Citizen API

No authentication. Anonymous. Stores nothing.

| Path | Purpose |
|---|---|
| `POST /parakh/analyze` | Analyse a message or Hinglish/English text |
| `POST /parakh/url/analyze` | Analyse a URL |
| `POST /parakh/email/analyze` | Analyse a raw .eml or email headers |
| `POST /parakh/check-before-open` | Quick pre-open risk check |
| `POST /parakh/report-to-police` | Citizen report (consent-gated, ephemeral) |

---

## Privacy & Security Design

| Property | Mechanism |
|---|---|
| **Citizen Mode never persists** | `create_case()` is never called from citizen routes; enforced by `test_citizen_mode_analysis_persists_nothing` |
| **SSRF guard** | Every outbound URL (including redirect hops) is checked against RFC-1918, loopback, link-local and ::1 before connecting |
| **APK analysis is offline** | Static only — no APK is executed, no Android SDK required, no emulator |
| **Website analysis is guarded** | 2 MB stream cap, 10 s timeout, 3 redirect hops max, no JavaScript execution |
| **Passwords use scrypt** | `hashlib.scrypt` — no native-wheel dependency, no passlib/bcrypt |
| **Tokens are hashed** | Only `SHA-256(token)` is stored; the raw token is never persisted |
| **No foreign-key silent failures** | SQLite `PRAGMA foreign_keys=ON` set per connection via SQLAlchemy connect-event |
| **APK size limit** | 60 MB hard cap (`MAX_APK_UPLOAD_BYTES`), enforced before parse |
| **Report content is HTML-escaped** | `html.escape()` on all user-supplied fields in `report_builder.py` |

---

## Known Limitations

| Limitation | Consequence |
|---|---|
| SQLite single-writer | Not suitable for concurrent production write load; swap `DATABASE_URL` for `postgresql+asyncpg://` for deployment |
| No runtime sandbox | APK analysis is static only — a highly obfuscated APK may not reveal its true behaviour |
| AI provider dependency | Gemini is used for natural-language analysis; a full rule-based fallback runs when the provider is unavailable |
| RDAP coverage | Some registrars do not publish RDAP; domain age may read as "unknown" for those |
| Windows asyncio limitation | 6 tests are skipped on Windows due to asyncio self-pipe constraints (B-4); they pass on Linux/macOS |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2 async |
| Database | SQLite + aiosqlite (dev/demo), PostgreSQL-ready |
| AI | Google Gemini via `google-genai` |
| APK parsing | `pyaxmlparser`, `asn1crypto`, `Pillow` (dHash) |
| URL intelligence | `tldextract`, RDAP, SSRF-guarded HTTP client |
| Frontend | React 19, Vite 8, Tailwind v4, Framer Motion |
| Testing | pytest-asyncio, httpx, Playwright (E2E) |

---

## Hackathon

Built for **Rajasthan Police Hackathon 2026 — PS01**
*Scam Message & Phishing Link Detection with Fake Loan / Investment App and Fraudulent Website Analysis*

PARAKH was developed as a conversion of the SurakshAI-India codebase, adapted end-to-end for PS01's investigation-first requirements while preserving a citizen-safety mode so the public can also benefit from the detection engine.

---

*PARAKH — परख | परखो, फिर भरोसो*
