<div align="center">

# 🔍 PARAKH — परख
### *परखो, फिर भरोसो &nbsp;|&nbsp; Test Before You Trust*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hackathon](https://img.shields.io/badge/Rajasthan%20Police-Hackathon%202026-blue?style=flat)](https://)

**Built for Rajasthan Police Hackathon 2026 — Problem Statement PS01**

*Scam Message & Phishing Link Detection with Fake Loan/Investment App and Fraudulent Website Analysis*

---

[🚀 Quick Start](#-quick-start-one-command) · [✨ Features](#-key-features) · [🏗️ Architecture](#-architecture) · [📡 API Reference](#-api-reference) · [☁️ Deploy on Vercel](#-deploy-on-vercel)

</div>

---

## 🚨 The Problem

India is in the middle of a **digital fraud epidemic**. Every day, millions of citizens receive:

- 📱 **Fake SMS/WhatsApp messages** — impersonating banks, KYC portals, government agencies
- 🔗 **Phishing links** — lookalike URLs stealing credentials and OTPs
- 📦 **Malicious APKs** — fake loan apps that harvest contacts, SMS, and photos for harassment
- 🌐 **Fraudulent websites** — Ponzi schemes, MLM traps, fake investment platforms

> 💔 **The Core Failure:** These threats reuse the same domains, phone numbers, UPI IDs, and payment accounts — but are **reported and investigated in isolation**. A phone number used in an SMS scam today is in a malicious APK tomorrow and a betting site the day after. No one connects the dots.

**Current gaps for law enforcement:**
- No unified platform to analyze all fraud artifact types
- Extracted evidence is not stored or searchable across cases
- No identifier linking between messages, apps, and websites
- Officers rely on manual pattern-matching across disconnected reports

---

## 💡 Our Solution

**PARAKH** (*परख* = *the touchstone test*) is a **dual-mode AI-powered investigation platform** that:

1. **Analyzes** any suspicious artifact — message, URL, email, APK, or website
2. **Extracts** 14 types of identifiers (UPI IDs, phone numbers, crypto wallets, etc.)
3. **Links** cases automatically when they share identifiers — revealing fraud campaigns
4. **Stores** everything searchable for officers while **storing nothing** for citizens

```
A jeweler uses a touchstone to test gold purity before accepting it.
PARAKH applies that same rigour to digital fraud — every suspicious
message, link, or app is tested before you trust it.
```

---

## 🚀 Quick Start (One Command)

> **Just clone and run. That's it. No manual setup needed.**

```bash
# 1. Clone the repository
git clone https://github.com/YaduvanshiHimanshunfsu/PARAKH.git
cd PARAKH

# 2. Copy and configure environment
cp .env.example .env
# Edit .env — set OFFICER_USERNAME and OFFICER_PASSWORD

# 3. Launch everything with a single command
python run.py
```

`run.py` is a **smart orchestrator** that automatically:
- ✅ Creates a Python virtual environment if missing
- ✅ Installs all backend Python dependencies (`requirements.txt`)
- ✅ Installs all frontend Node.js dependencies (`npm install`)
- ✅ Starts the FastAPI backend on `http://localhost:8000`
- ✅ Starts the React frontend on `http://localhost:5173`
- ✅ Runs both concurrently with prefixed log output

**That's it.** Open your browser:

| URL | Purpose |
|---|---|
| `http://localhost:5173` | Citizen Mode — analyze suspicious content |
| `http://localhost:5173/investigate` | Officer Console — full investigation dashboard |
| `http://localhost:8000/docs` | Interactive API documentation (Swagger UI) |

> **Prerequisites:** Python 3.11+ and Node.js 18+ must be installed on your system.

### Demo Data (Optional but Recommended)

```bash
# After first run.py, in a new terminal:
.venv\Scripts\python -m app.db.seed          # Seed blacklist database
.venv\Scripts\python -m app.db.demo_seed     # Load 14 cross-linked demo cases
```

---

## ✨ Key Features

### 🔄 Dual-Mode by Design

| Feature | 👥 Citizen Mode | 🚔 Officer Mode |
|---|---|---|
| **Who uses it** | Anyone — public facing | Rajasthan Police officers |
| **Authentication** | None required | Bearer token (login required) |
| **Data storage** | ❌ Nothing stored | ✅ Full case history |
| **Analysis** | Full AI analysis | Full AI analysis + case creation |
| **Report download** | Redacted PDF | Full investigation report |

### 🔬 Multi-Artifact Analysis Engine

| Artifact Type | What Gets Analyzed |
|---|---|
| 📱 **SMS / WhatsApp / Text** | 11 scam categories, 8 manipulation tactics, red-flag phrases |
| 🔗 **URLs & Links** | 9 risk signals, TLS check, domain age (RDAP), redirect chains |
| 📧 **Email (.eml)** | SPF/DKIM/DMARC headers, attachment risk, spoofing detection |
| 📦 **Android APK** | Permissions, manifest, signing certs, embedded URLs, icon similarity |
| 🌐 **Websites** | Page content scoring, Ponzi/MLM/betting language, identifier harvest |

### 🧩 14-Type Identifier Extraction

Every analysis automatically extracts and indexes:

```
📞 Phone numbers (E.164 normalized)    💳 UPI IDs (PSP-validated)
🏦 Bank accounts + IFSC codes         ₿  Crypto wallets (BTC, ETH)
🌐 URLs and domains                   📧 Email addresses
📍 IP addresses                       📱 Telegram handles
📦 Android package names              🏷️  App labels
🔐 Certificate SHA-256 fingerprints   📷 QR code payloads
🔑 App signing hashes                 🗂️  DEX embedded strings
```

### 🕸️ Cross-Case Identifier Linking

> **This is the core intelligence feature.**

When a phone number appears in an SMS, inside an APK, and on a fraudulent website — PARAKH **automatically links all three cases** and surfaces the full campaign picture.

- Weighted linking: shared UPI ID scores higher than a shared `bit.ly` link
- Near-duplicate detection using SimHash (character 5-grams) with ≤ 3-bit threshold
- Campaign clustering via connected components over the identifier graph
- Heat-list of trending scam identifiers (domains, phones, UPI IDs) with 7-day trend

### 🛡️ Unique Features

| Feature | Why It Matters |
|---|---|
| **Offline rule fallback** | Full scam detection even when Gemini AI is unavailable |
| **SSRF guard at every redirect hop** | Website analysis can't be used to probe internal networks |
| **Deterministic APK verdicts** | APK analysis never depends on AI availability |
| **SimHash similarity** | Detect SMS campaign templates with minor variations |
| **Citizen → Officer opt-in** | Citizens can optionally forward findings to the officer queue |
| **HTML-escaped reports** | `<script>` tags in scam content can't execute in reports |
| **Foreign key enforcement** | SQLite `PRAGMA foreign_keys=ON` — no silent data corruption |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                               │
│                                                             │
│  ┌──────────────────────┐   ┌────────────────────────────┐  │
│  │   Citizen SPA        │   │   Officer Console SPA      │  │
│  │  React 19 + Vite 8   │   │   /investigate routes      │  │
│  │  Tailwind v4         │   │   Bearer-token gated       │  │
│  └──────────┬───────────┘   └──────────────┬─────────────┘  │
└─────────────┼─────────────────────────────┼────────────────┘
              │                             │
              ▼ POST /api/v1/parakh/*       ▼ GET/POST /api/v1/investigate/*
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│                                                             │
│  ┌─────────────────┐   ┌─────────────────┐                 │
│  │  ScamAnalyzer   │   │  ArtifactAnalyzer│                │
│  │  (AI + Rules)   │   │  (unified seam)  │                │
│  └────────┬────────┘   └────────┬─────────┘                │
│           │                    │                            │
│  ┌────────▼────────────────────▼──────────────────────┐    │
│  │            IdentifierExtractor (14 types)           │    │
│  └────────────────────────┬───────────────────────────┘    │
│                           │                                  │
│  ┌──────────────┐  ┌──────▼───────┐  ┌──────────────────┐  │
│  │  ApkAnalyzer │  │  CaseService │  │  WebsiteAnalyzer │  │
│  │  (static,    │  │  (persist,   │  │  (guarded fetch, │  │
│  │  no AI)      │  │  search)     │  │  SSRF-safe)      │  │
│  └──────────────┘  └──────┬───────┘  └──────────────────┘  │
│                           │                                  │
│  ┌──────────────────────  │  ────────────────────────────┐  │
│  │  LinkService           │  SimHash · Identifier Graph  │  │
│  └────────────────────────┼──────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  SQLite + aiosqlite (dev)  │
              │  PostgreSQL-ready (prod)   │
              │                            │
              │  users · cases · findings  │
              │  identifiers · blacklist   │
              │  domain_intel              │
              └────────────────────────────┘
```

### Analysis Flow

```
                     User Input
                         │
           ┌─────────────┼──────────────┐
           ▼             ▼              ▼
         Text           URL           APK / Website
           │             │              │
           ▼             ▼              ▼
    ScamAnalyzer   URLIntelligence  ApkAnalyzer /
    (Gemini AI +   (9 signals +     WebsiteAnalyzer
     17 rules)      TLS + RDAP)     (fully deterministic)
           │             │              │
           └─────────────┼──────────────┘
                         ▼
              IdentifierExtractor
              (14 types, span-based
               overlap resolution)
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
       Citizen Mode  Officer Mode  Heat-list
       (ephemeral)   (persisted    (trending
                      + linked)    identifiers)
```

---

## 🔄 Workflow

```
┌──────────────────────────────────────────────────────────────┐
│  5-Minute Demo Flow                                          │
│                                                              │
│  1. Submit scam SMS ──► Risk verdict + extracted identifiers │
│           │                                                  │
│  2. Upload APK ──────► Same C2 domain appears ──► LINKED!   │
│           │                                                  │
│  3. Analyze website ─► Same UPI ID appears ──────► LINKED!  │
│           │                                                  │
│  4. Dashboard ───────► All 3 cases in one campaign          │
│           │                                                  │
│  5. Heat-list ───────► That UPI ID ranks #1 this week       │
│           │                                                  │
│  6. Download report ─► Print-ready HTML investigation report │
└──────────────────────────────────────────────────────────────┘
```

### Request Lifecycle

```
Request Received
      │
      ▼
Size Limit Check (3.25 MB global / 60 MB APK route)
      │
      ▼
Rate Limiter (20 req/min, 120/day anonymous)
      │
      ▼
Auth Check (citizen: none | officer: bearer token)
      │
      ▼
Artifact Analysis ──► AI (Gemini) ──► Offline Fallback if AI down
      │
      ▼
Identifier Extraction (14 types)
      │
      ├── Citizen Mode: Return result, store NOTHING
      │
      └── Officer Mode: Persist case + findings + identifiers
                              │
                              ▼
                    Link to existing cases via
                    shared identifiers + SimHash
```

---

## 🛠️ Technical Stack

| Layer | Technology | Why |
|---|---|---|
| **Backend** | Python 3.11+, FastAPI, Pydantic v2 | Async-native, auto-docs, strict validation |
| **AI Engine** | Google Gemini (`google-genai`) | Best-in-class Hindi/English understanding |
| **Offline Fallback** | 17 deterministic regex rules | Zero-dependency scam detection |
| **Database** | SQLite + aiosqlite (dev) | Zero infrastructure, demo-reliable |
| **ORM** | SQLAlchemy 2.0 async | One connection-string swap to PostgreSQL |
| **APK Parsing** | `pyaxmlparser`, `asn1crypto` | Lightweight, no Android SDK needed |
| **URL Intelligence** | `tldextract`, RDAP, `httpx` | SSRF-safe, no WHOIS dependency |
| **Frontend** | React 19, Vite 8, Tailwind v4 | Modern, fast, Devanagari-ready |
| **Animations** | Framer Motion | Smooth UX on evidence panels |
| **Testing** | pytest-asyncio, httpx, Playwright | 246 tests, 25 E2E browser checks |
| **Auth** | `hashlib.scrypt` + SHA-256 tokens | Zero native-wheel dependency on Python 3.14 |

### Why These Choices?

- **SQLite over Postgres for the demo** — No network dependency during live judging. Swap `DATABASE_URL` in `.env` for `postgresql+asyncpg://...` for production.
- **Deterministic APK/Website analysis** — The demo baseline showed Gemini returning HTTP 401 for 1113ms per request. APK and website verdicts never wait for AI.
- **`pyaxmlparser` over `androguard`** — androguard is 50× heavier; we only need manifest parsing.
- **SimHash over ML similarity** — 30 lines of code, no dependency, proven on real scam campaign variants.

---

## 📡 API Reference

### Citizen API (No Authentication)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/parakh/analyze` | Analyze a text message or Hinglish content |
| `POST` | `/api/v1/parakh/url/analyze` | Analyze a suspicious URL |
| `POST` | `/api/v1/parakh/email/analyze` | Analyze a raw `.eml` or email headers |
| `POST` | `/api/v1/parakh/check-before-open` | Pre-click risk check (fast, cached) |
| `POST` | `/api/v1/parakh/report-to-police` | Forward to officer queue (consent-gated) |

### Investigation API (Bearer Token Required)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/investigate/login` | Officer sign-in → bearer token |
| `POST` | `/api/v1/investigate/submit` | Analyze + persist as a case |
| `POST` | `/api/v1/investigate/apk/analyze` | Static APK analysis (upload) |
| `POST` | `/api/v1/investigate/website/analyze` | Guarded website fetch and analysis |
| `GET` | `/api/v1/investigate/cases` | Paginated case list (search, filter) |
| `GET` | `/api/v1/investigate/cases/{id}` | Full case detail |
| `PATCH` | `/api/v1/investigate/cases/{id}/status` | Update status + officer note |
| `DELETE` | `/api/v1/investigate/cases/{id}` | Soft delete |
| `GET` | `/api/v1/investigate/identifier/{value}/cases` | All cases sharing this identifier |
| `GET` | `/api/v1/investigate/cases/{id}/linked` | Cases linked by shared identifiers |
| `GET` | `/api/v1/investigate/cases/{id}/similar` | Near-duplicate content (SimHash) |
| `GET` | `/api/v1/investigate/heat-list` | Trending scam identifiers |
| `GET` | `/api/v1/investigate/export/cases.json` | Bulk JSON export |
| `GET` | `/api/v1/investigate/export/cases.csv` | Bulk CSV export |
| `GET` | `/api/v1/investigate/cases/{id}/report.html` | Print-ready HTML investigation report |

> **Full interactive docs:** `http://localhost:8000/docs` (Swagger UI) after starting the app.

---

## 🔒 Privacy & Security Design

| Property | Mechanism |
|---|---|
| **Citizen Mode never persists** | `create_case()` is never called from citizen routes; enforced by automated test |
| **SSRF guard** | Every outbound URL (including redirect hops) is checked against RFC-1918, loopback, and link-local ranges before connecting |
| **APK analysis is offline** | Static only — no APK is executed, no Android SDK required, no emulator needed |
| **Website analysis is guarded** | 2 MB stream cap, 10s timeout, 3 max redirects, no JavaScript execution |
| **Passwords use scrypt** | `hashlib.scrypt` — no native-wheel dependency |
| **Tokens are hashed** | Only `SHA-256(token)` is stored; raw token never persisted |
| **Report content is HTML-escaped** | `html.escape()` on all user-supplied fields — `<script>` tags in scam content can't execute |
| **Foreign keys enforced** | SQLite `PRAGMA foreign_keys=ON` per connection — cascade deletes work correctly |

---

## ☁️ Deploy on Vercel

The citizen-facing frontend and API are **Vercel-ready** out of the box.

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Deploy
vercel

# 3. Set environment variables in Vercel dashboard:
#    GEMINI_API_KEY=your_key_here
#    ENVIRONMENT=production
#    ALLOWED_ORIGINS=https://your-app.vercel.app
```

> **Important:** Vercel is ideal for the **Citizen Mode** (stateless, ephemeral). For **Investigation Mode** (which requires persistent SQLite storage and APK uploads up to 60 MB), deploy on a persistent host — a team laptop for demos, or Railway/Render/VPS for production. See [DECISIONS.md](DECISIONS.md) ADR-003 for the full rationale.

**Production Database:** Change one line in `.env`:
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
```
No code changes needed — SQLAlchemy handles the rest.

---

## 📋 PS01 Compliance Checklist

| PS01 Requirement | ✅ PARAKH Implementation |
|---|---|
| Analyze a message or URL → risk level + reasons | `POST /parakh/analyze` + `POST /parakh/url/analyze` — Low/Medium/High with per-finding explanations |
| Analyze at least one APK **or** one website | APK static analysis (permissions, manifest, certs, dHash) **AND** website analysis (guarded fetch, identifier harvesting) — **both** implemented |
| Extract URLs, phone numbers, UPI IDs from artifacts | 14 identifier types including UPI, phone, URL, domain, email, bank account, Telegram, crypto wallet |
| Dashboard with case history, search, downloadable report | Officer console at `/investigate` — paginated search, identifier linking, heat-list, JSON/HTML/CSV export |
| Cross-source identifier linking | `GET /investigate/identifier/{value}/cases` — weighted linking by identifier rarity |
| Heat-list of trending scam identifiers | `GET /investigate/heat-list` — ranked with 7-day trend delta |

---

## ⚠️ Known Limitations

| Limitation | Consequence |
|---|---|
| SQLite single-writer | Not suitable for high concurrent write load; swap to PostgreSQL for production |
| Static APK analysis only | Highly obfuscated or packed APKs may reveal less; dynamic sandboxing is out of scope |
| AI provider dependency | Gemini used for natural-language analysis; full rule-based fallback runs when unavailable |
| JS-rendered websites | Sites requiring JavaScript execution return thin HTML content; stated in analysis output |
| RDAP coverage | Some registrars don't publish RDAP; domain age may read as "unknown" |
| Windows asyncio | 6 tests skipped on Windows (asyncio self-pipe); they pass on Linux/macOS |

---

## 🗂️ Project Structure

```
PARAKH/
│
├── run.py                    ← 🚀 Single-command launcher (start here!)
├── requirements.txt          ← Python dependencies
├── vercel.json               ← Vercel deployment config
├── .env.example              ← Environment template (copy to .env)
│
├── app/                      ← FastAPI backend
│   ├── main.py               ← App entry point, middleware
│   ├── config.py             ← Pydantic settings
│   ├── schemas.py            ← Request/response models
│   ├── prompts.py            ← Gemini AI prompt templates
│   │
│   ├── api/                  ← Route handlers
│   │   ├── routes.py         ← Citizen API (/parakh/*)
│   │   └── investigate.py    ← Officer API (/investigate/*)
│   │
│   ├── services/             ← Business logic
│   │   ├── scam_analyzer.py  ← Text/SMS/WhatsApp analysis
│   │   ├── url_intelligence.py ← URL risk analysis
│   │   ├── artifact_analyzer.py ← Unified analysis seam
│   │   ├── apk_analyzer.py   ← APK static analysis
│   │   ├── apk_parsing.py    ← APK container + manifest
│   │   ├── website_analyzer.py ← Guarded website fetch
│   │   ├── identifier_extractor.py ← 14-type extractor
│   │   ├── case_service.py   ← Case CRUD + persistence
│   │   ├── link_service.py   ← Identifier linking + SimHash
│   │   ├── url_enrichment.py ← RDAP, redirects, blacklist
│   │   └── report_builder.py ← HTML investigation reports
│   │
│   ├── data/                 ← Detection rules (version-controlled)
│   │   ├── scam_rules.py     ← 17 offline scam rules
│   │   ├── apk_permission_rules.py ← APK danger permissions
│   │   ├── website_rules.py  ← Ponzi/MLM/betting patterns
│   │   └── blacklists.py     ← Domain/phone/UPI blacklists
│   │
│   ├── db/                   ← Database layer
│   │   ├── models.py         ← SQLAlchemy ORM models
│   │   ├── session.py        ← Async session factory
│   │   ├── seed.py           ← Blacklist seeder
│   │   └── demo_seed.py      ← 14 cross-linked demo cases
│   │
│   ├── core/                 ← Cross-cutting concerns
│   │   ├── auth.py           ← Officer auth (scrypt + SHA-256)
│   │   ├── middleware.py     ← CSP, HSTS, size limits
│   │   ├── redis_limiter.py  ← Hybrid rate limiting
│   │   └── monitoring.py     ← Health checks
│   │
│   └── utils/
│       └── fingerprint.py    ← SimHash implementation
│
├── frontend/                 ← React 19 + Vite 8 SPA
│   ├── src/
│   │   ├── app/              ← Routing, layout, auth context
│   │   ├── features/         ← UI feature components
│   │   │   └── investigate/  ← Officer console components
│   │   ├── pages/investigate/← Officer pages (login, cases, etc.)
│   │   └── lib/              ← API clients, report generator
│   └── dist/                 ← Pre-built assets (committed for Vercel)
│
└── tests/                    ← 246 tests, 25 E2E browser checks
    ├── test_api.py
    ├── test_investigation_api.py
    ├── test_apk_analyzer.py
    ├── test_website_analyzer.py
    ├── test_identifier_extractor.py
    ├── test_link_service.py
    ├── test_ssrf_guard.py
    └── ...
```

---

## 🧪 Running Tests

```bash
# Activate virtual environment first
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

# Run the full test suite
pytest

# Expected: 246 passed, 6 skipped (Windows asyncio), 0 failed
```

---

## 🏁 Conclusion

PARAKH is not just a scam detector — it is a **fraud intelligence platform** designed around the real workflow of a police investigation.

**What makes PARAKH different:**

| Others | PARAKH |
|---|---|
| Analyze one message at a time | Analyze messages, URLs, APKs, emails, and websites |
| Return a verdict and forget | Build a searchable case history |
| Miss the connection between fraud artifacts | **Link cases automatically via shared identifiers** |
| Fail when AI is unavailable | Full offline rule-based fallback for all artifact types |
| Store everything or nothing | Dual-mode: citizen privacy + officer persistence |

**In a live demo, PARAKH can show:** an SMS, an APK, and a fraudulent website — submitted separately — automatically resolved into a single fraud campaign, with the shared UPI ID appearing at the top of the heat-list, all three cases linked, and a print-ready investigation report generated in under a second.

That is the fragmentation problem PS01 describes. That is what PARAKH solves.

---

<div align="center">

**Built with ❤️ for Rajasthan Police Hackathon 2026**

Developed by **Himanshu Yadav** · `himanshu.btmtcs4242906@nfsu.ac.in` · National Forensic Sciences University

*PARAKH — परख | परखो, फिर भरोसो*

</div>
