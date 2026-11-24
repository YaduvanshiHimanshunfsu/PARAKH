<div align="center">

# 🔍 PARAKH — परख
### *परखो, फिर भरोसो &nbsp;|&nbsp; Test Before You Trust*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev)
[![Tests](https://img.shields.io/badge/Tests-541%20backend%20%7C%20151%20frontend-brightgreen?style=flat)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**🏆 Rajasthan Police Hackathon 2026 — Problem Statement PS01**

*Scam Message & Phishing Link Detection with Fake Loan/Investment App and Fraudulent Website Analysis*

---

**Team Gravity**

| 👤 Member | 🎓 Role |
|---|---|
| **Himanshu Yadav** | Lead Developer & AI/Backend Architect |
| **Gaurav Raj** | Frontend & UX Engineer |
| **Umesh Gupta** | Research & Data / Testing Lead |

---

[🚀 Quick Start](#-quick-start) · [🚨 Problem](#-problem-statement) · [💡 Solution](#-our-solution) · [✨ Features](#-key-features) · [🏗️ Architecture](#-architecture--workflow) · [🛠️ Tech Stack](#-tech-stack) · [☁️ Deploy](#-deployment) · [📄 Docs](docs/)

</div>

---

## 🚨 Problem Statement

India is facing a **digital fraud epidemic** at scale. Every day, millions of citizens receive:

| Threat | Example |
|---|---|
| 📱 **Fake SMS / WhatsApp** | "Your SBI KYC will expire in 24 hours. Click sbi-verify-kyc.in/urgent" |
| 🔗 **Phishing links** | Lookalike URLs stealing OTPs and credentials |
| 📦 **Malicious APKs** | Fake loan/investment apps that harvest contacts, SMS, and photos |
| 🌐 **Fraud websites** | Ponzi schemes, MLM traps, fake SEBI/RBI-approved investment platforms |
| 📧 **Spoofed emails** | Fake government/bank emails with forged headers |
| 📸 **QR code fraud** | Malicious QR codes embedded in messages and websites |

### The Core Gap

> These threats **reuse the same infrastructure** — the same phone number in an SMS scam is embedded in a malicious APK and listed on a fraudulent website. Yet investigations happen in **complete isolation**. No officer connects the dots. No system links the evidence.

**Current pain points for law enforcement:**

- ❌ No unified analysis across message types, APKs, URLs, and websites
- ❌ Extracted evidence is not stored, searchable, or linked across cases
- ❌ Manual pattern-matching across disconnected FIRs
- ❌ Investigation teams cannot see that 50 complaints share the same UPI ID
- ❌ No heat-map of which fraud campaigns are active right now in Rajasthan

---

## 💡 Our Solution

**PARAKH** (*परख* = *the touchstone test a jeweler uses to verify gold purity*) is a **dual-mode AI-powered fraud investigation platform** built specifically for the Indian cyber-fraud context.

```
Every suspicious message, link, APK, or website is tested on the touchstone
before you trust it — just like a jeweler tests gold before accepting it.
```

### Two modes. One engine. One truth.

| Mode | Who | Privacy | Storage |
|---|---|---|---|
| 👥 **Citizen Mode** | Any member of the public | Fully ephemeral — nothing stored | ❌ Zero |
| 🚔 **Officer Mode** | Rajasthan Police officers (bearer-token gated) | Full case history, searchable | ✅ Full |

**The key insight:** by running both modes on the same analysis engine, citizens get instant fraud detection while officers get a growing intelligence database — without compromising anyone's privacy.

---

## 🚀 Quick Start

> **Clone → Configure → Run. One command starts everything.**

### Prerequisites
- Python 3.11+ 
- Node.js 18+

```bash
# 1. Clone the repository
git clone https://github.com/YaduvanshiHimanshunfsu/PARAKH.git
cd PARAKH

# 2. Configure environment
cp .env.example .env
# Open .env and set:
#   OFFICER_USERNAME=officer
#   OFFICER_PASSWORD=YourSecurePasswordHere
#   GEMINI_API_KEY=your_key_here   (optional — works offline without it)

# 3. Launch with a single command
python run.py
```

`run.py` automatically:
- ✅ Creates the Python `.venv` if it doesn't exist
- ✅ Installs all backend dependencies from `requirements.txt`
- ✅ Installs all frontend Node.js dependencies (`npm install`)
- ✅ Starts the FastAPI backend on **http://localhost:8000**
- ✅ Starts the React frontend on **http://localhost:5173**
- ✅ Runs both concurrently with prefixed colour-coded logs

### Open in your browser

| URL | Purpose |
|---|---|
| `http://localhost:5173` | 👥 Citizen Mode — submit suspicious content |
| `http://localhost:5173/officer` | 🚔 Officer Console — full investigation dashboard |
| `http://localhost:8000/docs` | 📡 Swagger UI — interactive API reference |

### Load Demo Data (Recommended)

```bash
# Recreate the schema and load 14 cross-linked demo cases
.venv\Scripts\python scripts/reset_demo_db.py --yes

# Create the police hierarchy and the officer accounts below
.venv\Scripts\python scripts/seed_demo_officers.py
```

### 👮 Demo officer accounts

> ⚠️ **Demonstration accounts only.** They share one password so a reviewer can
> switch roles in seconds. A real deployment issues one password per officer,
> set at first sign-in. PARAKH stores only a hash, and the lockout, MFA and
> audit controls apply to these accounts exactly as they would to real ones.

**Password for every account: `ParakhDemo@2026`**

| Username | Rank | Role | Unit | What this role can do |
|---|---|---|---|---|
| `io.si.sharma` | SI | IO | Cyber PS, Jaipur | Works cases, drafts requisitions — **cannot approve** |
| `sho.cyber` | Inspector | STATION_HEAD | Cyber PS, Jaipur | Station approval · assigns and transfers cases |
| `sp.jaipur` | SP | SUPERVISOR | Jaipur Commissionerate | District approval — **required for every freeze** |
| `dysp.cyber` | DySP | SUPERVISOR | Jaipur Commissionerate | District approval |
| `op.hc` | HC | OPERATOR | Cyber PS, Jaipur | Submits items; sees only their own submissions |
| `io.btp` | Inspector | IO | Cyber PS, **Bharatpur** | Different district — **cannot see Jaipur's cases at all** |
| `viewer.state` | ADG | STATE_VIEWER | State HQ | Read-only across the whole state |

Run `python scripts/seed_demo_officers.py --show` to print this table at any time.

---

## 🗺️ Wireframe & UI Flow

![PARAKH Wireframe](wireframe.jpg)

The UI is built from the **Civic Vigilance Light** design system (31 screens) covering:
- Citizen: Home → Check → Result → Evidence Locker → Rescue Guide → Status Tracker
- Officer: Login → Dashboard → Cases → Case Detail → Campaigns → Heat-list → Queue → Reports

### 📸 The running system

*Every screenshot below is the real application, captured against a live server.*

| Officer case file with the **action pack** | Approval **queue** |
|---|---|
| ![Case file with action pack](docs/images/officer-case-action-pack.png) | ![Approval queue](docs/images/officer-approval-queue.png) |

| Command dashboard | Campaign map |
|---|---|
| ![Command dashboard](docs/images/officer-command-dashboard.png) | ![Campaign map](docs/images/officer-campaign-map.png) |

| Citizen verdict, with red flags highlighted | Rescue plan (mobile, 390 px) |
|---|---|
| ![Citizen verdict](docs/images/citizen-result.png) | ![Rescue plan](docs/images/citizen-rescue-mobile.png) |

---

## 🔄 Architecture & Workflow

```
 ┌─────────────────────────────────────────────────────────────────────┐
 │                           BROWSER                                   │
 │                                                                     │
 │   ┌──────────────────────────┐   ┌─────────────────────────────┐   │
 │   │     Citizen SPA          │   │     Officer Console SPA      │   │
 │   │  React 19 + Tailwind v4  │   │  Bearer-token gated routes   │   │
 │   │  Hindi/English bilingual │   │  Dashboard · Cases · Reports │   │
 │   │  Offline-capable         │   │  Campaigns · Heat-list       │   │
 │   └──────────┬───────────────┘   └───────────────┬─────────────┘   │
 └──────────────┼───────────────────────────────────┼─────────────────┘
                │ POST /api/v1/parakh/*              │ GET/POST /api/v1/investigate/*
 ┌──────────────▼───────────────────────────────────▼─────────────────┐
 │                        FastAPI Backend                              │
 │                                                                     │
 │  ┌───────────────────────────────────────────────────────────────┐  │
 │  │                    Analysis Engine                             │  │
 │  │                                                               │  │
 │  │  ScamAnalyzer   URLIntelligence  ApkAnalyzer  WebsiteAnalyzer │  │
 │  │  (Gemini AI +   (9 signals,      (static,      (guarded HTTP  │  │
 │  │   17+ rules,    TLS, RDAP,       no AI,        fetch, SSRF    │  │
 │  │   offline-first) redirect chains) deterministic) safe)        │  │
 │  │          │             │               │              │        │  │
 │  │          └─────────────┴───────────────┴──────────────┘        │  │
 │  │                        │                                        │  │
 │  │              IdentifierExtractor                                │  │
 │  │              (14 types: UPI, phone, BTC, ETH,                  │  │
 │  │               IFSC, bank a/c, Telegram, domain,                │  │
 │  │               email, IP, pkg, cert, QR, USDT)                  │  │
 │  └───────────────────────────────────────────────────────────────┘  │
 │                            │                                        │
 │       ┌────────────────────┼────────────────────┐                   │
 │       ▼                    ▼                    ▼                   │
 │  Citizen Mode         Officer Mode           Link Service           │
 │  (return result,      (persist case,         (SimHash similarity,   │
 │   store NOTHING)      find links,             identifier graph,      │
 │                       build heat-list)        campaign clustering)  │
 └───────────────────────────┬────────────────────────────────────────┘
                             │
              ┌──────────────▼────────────────┐
              │  SQLite + aiosqlite (dev)      │
              │  PostgreSQL-ready (prod)        │
              │                                │
              │  cases · findings · identifiers│
              │  users · units · blacklist     │
              │  domain_intel · audit_log      │
              └────────────────────────────────┘
```

### Request Lifecycle

```
User Input (Message / URL / Email / APK / Website / QR)
        │
        ▼
  Request Size Check ──► Rate Limiter ──► Auth Check
        │                                      │
        │                              Citizen: none
        │                              Officer: bearer token
        ▼
  Multi-layer Analysis
  ┌────────────────────────────────────────────────┐
  │  Layer 1: Deterministic Rules (always runs)    │
  │  Layer 2: Gemini AI enrichment (if available)  │
  │  Layer 3: AI Fusion Guardrail                  │
  │    (AI cannot lower a HIGH rule verdict)       │
  └────────────────────────────────────────────────┘
        │
        ▼
  Identifier Extraction (14 types)
        │
        ├──► Citizen Mode: return result → store NOTHING
        │
        └──► Officer Mode: persist case + findings + identifiers
                               │
                               ▼
                    Link to existing cases via
                    shared identifiers + SimHash
                               │
                               ▼
                    Update heat-list + campaign graph
```

### 5-Minute Demo Flow

```
1. Submit scam SMS ──────────► Risk verdict + 14-type identifier extraction
         │
         └──► Same phone number already in DB → LINKED to 2 prior cases

2. Upload malicious APK ─────► Permissions, cert, embedded C2 domain extracted
         │
         └──► Same C2 domain as the SMS → LINKED! Campaign detected.

3. Analyze fraudulent website ► Ponzi language scored, UPI ID harvested
         │
         └──► Same UPI ID as APK → LINKED! Same fraud operator confirmed.

4. Officer Dashboard ────────► All 3 cases in one campaign, heat-list updated
         │
         └──► Download print-ready HTML investigation report
```

### ⛓️ Chain of command — the part most tools stop short of

Detection without action is a dashboard. PARAKH turns a case into the
paperwork an investigation actually needs, and routes it through the real
hierarchy.

```
  IO opens the case  ──►  "Draft requisitions"
        │                  PARAKH groups the case's SUSPECT identifiers by
        │                  (document type, addressee) and drafts ONE notice
        │                  per group — not one per identifier
        ▼
  5 unsigned DRAFTS, each watermarked, each citing its legal basis
        │
        ▼
  IO submits the freeze request        ⏱ SLA starts: 2 hours (golden hour)
        │
        ├──► IO tries to approve it    ──►  ❌ REFUSED
        │                                   the drafter may never approve
        │                                   their own document
        ▼
  sho.cyber (Inspector) approves       ✅ station level
        │
        ▼
  sp.jaipur (SP) approves              ✅ a freeze ALWAYS needs the district
        │
        ▼
  APPROVED ──► dispatch recorded ──► the bank's reply recorded on the case
        │
        ▼
  Every step above is in the tamper-evident audit chain
```

**Try it yourself in 9 steps:**

| # | As | Do this | What you should see |
|---|---|---|---|
| 1 | *(citizen)* | Paste a scam SMS and check it | HIGH risk, exact words highlighted, Hindi explanation |
| 2 | *(citizen)* | Tick consent → **Send to police** | A reference number you can track |
| 3 | `io.si.sharma` | Open the case → **Draft requisitions** | 5 drafts: freeze, bank records, telecom, Chakshu, §63 certificate |
| 4 | `io.si.sharma` | Submit the freeze → try to approve it | **403** — separation of duties |
| 5 | `sho.cyber` | **My queue** → approve | Status becomes *With supervisor* |
| 6 | `sp.jaipur` | Approve → record dispatch | **APPROVED** → **DISPATCHED** |
| 7 | `sho.cyber` | Assign the case to `io.si.sharma` as an *IT Act* offence | **422** — IT Act §78 needs Inspector or above |
| 8 | `io.btp` | Open that same Jaipur case | **404** — jurisdiction scoping (not 403: a 403 would confirm it exists) |
| 9 | any officer | Open the case's **audit trail** | *"Audit chain verified (N events)."* |

### 📊 The eight requisition types PARAKH drafts

| Document | Legal basis | Approval needed | SLA |
|---|---|---|---|
| Hold disputed funds | **BNSS 2023 §106** | Station **+ district** | 2 h |
| Produce bank documents | **BNSS 2023 §94** | Station (district above ₹10 L) | 24 h |
| Telecom CAF / CDR | **BNSS 2023 §94** | Station | 24 h |
| Fraud number report | DoT Sanchar Saathi | Station | 24 h |
| Domain takedown | **IT Act §79(3)(b)** | Station + district | 24 h |
| Hosting abuse notice | **IT Act §79(3)(b)** | Station | 24 h |
| Intermediary takedown | **IT Act §79(3)(b)** | Station + district | 24 h |
| Electronic evidence certificate | **BSA 2023 §63** | Station | 48 h |

Every draft carries a **DRAFT** watermark and an **empty signature block** —
PARAKH never renders a signature or a seal. Where a mapping can change (a UPI
handle's sponsor bank, a number that may have been ported) the draft says
*"confirm before dispatch"* instead of asserting it.

---

## ✨ Key Features

### 🔬 6-Artifact Analysis Engine

| Artifact | What PARAKH Analyzes |
|---|---|
| 📱 **SMS / WhatsApp / Hinglish text** | 11 scam categories, 8 manipulation tactics, Devanagari-aware rules |
| 🔗 **URLs & Links** | 9 risk signals, TLS check, domain age via RDAP, full redirect chain |
| 📧 **Email (raw .eml)** | SPF / DKIM / DMARC headers, spoofing detection, attachment risk |
| 📦 **Android APK** | Permissions, manifest, signing certs (v1/v2/v3), DEX strings, icon similarity |
| 🌐 **Websites** | Ponzi/MLM/betting language, page content scoring, identifier harvest |
| 📸 **QR codes** | Decode embedded URLs, run full URL analysis on the payload |

### 🧩 14-Type Identifier Extraction

Every analysis extracts, normalizes, and indexes:

```
📞 Indian phone numbers (E.164)      💳 UPI IDs (PSP-validated)
🏦 Bank accounts + IFSC codes        ₿  Bitcoin wallets (Legacy + Bech32)
🔷 Ethereum / USDT-ERC20             🟡 USDT-TRC20 (TRX addresses)
🌐 URLs and domains                  📧 Email addresses
📍 IP addresses (not version strings) 📱 Telegram handles + t.me links
📦 Android package names             🔐 Certificate SHA-256 fingerprints
📷 QR code payloads                  🏷️  App labels
```

### 🕸️ Cross-Case Intelligence Graph

> **This is what makes PARAKH a platform, not just a scanner.**

```
SMS case ──[phone +91-9812345670]──► APK case ──[UPI richplan@ybl]──► Website case
   │                                     │                                │
   └──────── SAME CAMPAIGN ──────────────┴────────────────────────────────┘
              Shared identifiers: phone, UPI, C2 domain
              Heat-list rank: UPI #1 this week (3 cases, rising)
```

- **Weighted linking:** shared UPI ID scores 10×; shared `bit.ly` link scores 1×
- **SimHash similarity:** detect SMS campaign templates with minor word-swap variations (character 5-grams, Hamming distance ≤ 3)
- **Campaign clustering:** connected-component graph over identifier overlap
- **Heat-list:** top scam domains, phones, UPI IDs, packages — with 7-day trend arrows

### 🛡️ Unique Features

| Feature | Why It Matters |
|---|---|
| **AI Fusion Guardrail** | Gemini AI can *raise* a verdict (more context), never *lower* a strong rule hit |
| **Offline-first analysis** | Full scam detection with no API key, no internet — demo-reliable |
| **SSRF guard at every redirect hop** | Website fetching cannot probe internal police network ranges |
| **Deterministic APK verdicts** | APK analysis never hangs on AI availability |
| **Hindi/Hinglish Devanagari rules** | Catches "आपका account बंद हो जाएगा" that Latin-only rules miss |
| **Known-site whitelist** | `police.rajasthan.gov.in`, `cybercrime.gov.in` are never flagged BRAND_LIKE |
| **Officer hierarchy + jurisdiction** | SP → DySP → SHO → IO → Operator with jurisdiction scoping |
| **Approval chain + MIS** | Requisitions, dispatch, action packs with full audit trail |
| **Bilingual UI** | Hindi and English — citizens choose their language |
| **Evidence locker** | AES-GCM encrypted browser-local evidence (IndexedDB, non-extractable key) |
| **Citizen → Officer opt-in** | Citizens can optionally forward findings to the officer queue |

---

## 🛠️ Tech Stack

| Layer | Technology | Version | Why We Chose It |
|---|---|---|---|
| **Backend framework** | FastAPI | 0.115+ | Async-native, automatic OpenAPI docs, Pydantic validation |
| **AI engine** | Google Gemini (`google-genai`) | 2.0+ | Best Hindi/Hinglish understanding; structured JSON output mode |
| **Offline fallback** | Custom rule engine | — | 17+ deterministic rules — zero AI dependency for verdict |
| **APK parsing** | `pyaxmlparser` | 0.3.31+ | v1/v2/v3 signatures, manifest, permissions — no Android SDK needed |
| **Phone parsing** | `phonenumbers` | 8.13+ | E.164 normalization, region detection — no false positives |
| **QR decoding** | `zxing-cpp` | 2.2+ | Server-side QR decode from images on fetched pages |
| **URL intelligence** | `tldextract` + `httpx` + RDAP | — | SSRF-safe, no WHOIS dependency, hop-by-hop redirect chains |
| **HTML parsing** | `BeautifulSoup4` | 4.12+ | Extract page text, links, forms, scripts for website analysis |
| **Email auth** | `dkimpy` + `dnspython` | — | DKIM signature verification, SPF/DMARC header analysis |
| **Database ORM** | SQLAlchemy 2.0 async | 2.0+ | One connection-string swap to PostgreSQL; no SQLite-specific SQL |
| **Database (dev)** | SQLite + `aiosqlite` | — | Zero infrastructure, demo-reliable, no network dependency |
| **Auth** | `hashlib.scrypt` + SHA-256 tokens | stdlib | No native-wheel dependency on Python 3.11+/3.14 |
| **Similarity** | Custom SimHash | — | 30 lines, no dependency, character 5-grams beat word n-grams on scam variants |
| **Frontend** | React 19 + Vite 8 | — | Modern, fast hot-reload, tree-shaking |
| **Styling** | Tailwind CSS v4 | 4+ | Civic Vigilance Light design system tokens |
| **Animations** | Framer Motion | — | Smooth evidence panel transitions |
| **i18n** | Custom `i18n.jsx` | — | Hindi/English toggle, no heavy library needed |
| **Charts** | Recharts | — | Campaign graph, heat-list trends |
| **Geo visualization** | TopoJSON + D3 | — | India district heat-map (Rajasthan highlight) |
| **Testing (backend)** | pytest-asyncio + httpx | — | 320 tests, all pass with no API key |
| **Testing (frontend)** | Vitest + Playwright | — | 94 unit tests + 84 E2E browser checks |
| **Error monitoring** | Sentry SDK | 2.0+ | Privacy-scrubbed; does nothing without `SENTRY_DSN` |
| **MFA** | `pyotp` (TOTP) | 2.9+ | Optional for Supervisor/Admin accounts |

---

## 🏗️ Project Structure

```
PARAKH/
│
├── run.py                      ← 🚀 Single-command launcher (start here!)
├── requirements.txt            ← Python dependencies
├── vercel.json                 ← Vercel deployment config
├── wireframe.jpg               ← UI wireframe reference
├── .env.example                ← Environment template (copy to .env)
│
├── app/                        ← FastAPI backend
│   ├── main.py                 ← App entry, middleware, SPA mount
│   ├── config.py               ← Pydantic settings (all from .env)
│   ├── schemas.py              ← Request/response models
│   ├── prompts.py              ← Gemini AI prompt templates
│   │
│   ├── api/                    ← Route handlers
│   │   ├── routes.py           ← Citizen API (/parakh/*)
│   │   ├── investigate.py      ← Officer API (/investigate/*)
│   │   ├── documents.py        ← Document/action pack API
│   │   └── uploads.py          ← File upload handling
│   │
│   ├── services/               ← Business logic (35 services)
│   │   ├── scam_analyzer.py    ← Text/SMS/WhatsApp + Gemini AI
│   │   ├── url_intelligence.py ← URL risk (9 signals + TLS + RDAP)
│   │   ├── artifact_analyzer.py← Unified analysis seam
│   │   ├── apk_analyzer.py     ← APK static analysis (v1/v2/v3 certs)
│   │   ├── apk_parsing.py      ← APK container + manifest parsing
│   │   ├── website_analyzer.py ← Guarded website fetch (SSRF-safe)
│   │   ├── email_analyzer.py   ← SPF/DKIM/DMARC + header analysis
│   │   ├── qr_analyzer.py      ← QR decode + URL analysis
│   │   ├── identifier_extractor.py ← 14-type identifier extraction
│   │   ├── case_service.py     ← Case CRUD + persistence
│   │   ├── link_service.py     ← Identifier linking + SimHash
│   │   ├── campaign_service.py ← Campaign clustering + timelines
│   │   ├── url_enrichment.py   ← RDAP, redirects, blacklist
│   │   ├── report_builder.py   ← HTML investigation reports
│   │   ├── workflow_service.py ← Approval chain + action packs
│   │   ├── mis_service.py      ← Management Information System
│   │   └── audit_service.py    ← Tamper-evident audit trail
│   │
│   ├── data/                   ← Detection rules (version-controlled)
│   │   ├── scam_rules.py       ← 17+ offline scam rules (Hinglish/Hindi)
│   │   ├── apk_permission_rules.py ← APK danger permissions + combos
│   │   ├── website_rules.py    ← Ponzi/MLM/betting patterns
│   │   ├── blacklists.py       ← Domain/phone/UPI blacklists
│   │   ├── known_sites.py      ← Trusted sites whitelist (gov.in, etc.)
│   │   ├── protected_brands.py ← Brand lookalike detection data
│   │   ├── approval_policy.py  ← Officer approval chain rules
│   │   └── rule_weights.json   ← Tunable signal weights
│   │
│   ├── db/                     ← Database layer
│   │   ├── models.py           ← SQLAlchemy ORM models
│   │   ├── session.py          ← Async session factory
│   │   ├── seed.py             ← Blacklist seeder
│   │   ├── demo_seed.py        ← 14 cross-linked demo cases
│   │   └── units_seed.py       ← Demo police units + officers
│   │
│   ├── core/                   ← Cross-cutting concerns
│   │   ├── auth.py             ← Officer auth (scrypt + SHA-256 tokens)
│   │   ├── middleware.py       ← CSP, HSTS, size limits
│   │   ├── permissions.py      ← Officer role/jurisdiction checks
│   │   ├── rate_limiter.py     ← Hybrid rate limiting
│   │   └── monitoring.py       ← Health check + per-analyser status
│   │
│   └── utils/
│       ├── fingerprint.py      ← SimHash implementation
│       ├── text_normalise.py   ← Unicode/Devanagari normalization
│       ├── lookalike.py        ← Brand lookalike detection
│       └── json_output.py      ← Structured Gemini output helpers
│
├── frontend/                   ← React 19 + Vite 8 SPA
│   └── src/
│       ├── app/                ← Routing, layouts, auth context
│       ├── features/
│       │   ├── citizen/        ← Public-facing screens
│       │   │   ├── home/       ← Hero + India fraud map
│       │   │   ├── check/      ← Submit form (message/URL/APK/QR)
│       │   │   ├── result/     ← Verdict + identifiers + actions
│       │   │   ├── rescue/     ← Recovery guide + emergency contacts
│       │   │   ├── evidence/   ← AES-GCM evidence locker
│       │   │   └── status/     ← Track reported case status
│       │   └── officer/        ← Police console
│       │       ├── DashboardPage.jsx  ← Analytics + live stats
│       │       ├── CasesPage.jsx      ← Search + filter cases
│       │       ├── CaseDetailPage.jsx ← Full case + linked cases
│       │       ├── campaigns/         ← Campaign graph + timelines
│       │       ├── HeatlistPage.jsx   ← Trending fraud identifiers
│       │       └── documents/         ← Action packs + requisitions
│       ├── design/ui/          ← Civic Vigilance Light component library
│       ├── content/            ← en.json + hi.json (bilingual)
│       └── geo/                ← India TopoJSON for district map
│
├── eval/                       ← Evaluation harness
│   ├── golden/                 ← Labelled test dataset
│   │   ├── messages_scam.jsonl ← Scam messages (ground truth)
│   │   ├── messages_safe.jsonl ← Safe messages (hard negatives)
│   │   ├── urls.jsonl          ← URL verdicts
│   │   ├── apks.json           ← APK verdicts
│   │   └── websites.jsonl      ← Website verdicts
│   ├── baseline.json           ← Measured baseline scores
│   ├── report.json / report.md ← Latest evaluation report
│   └── demo_cases.json         ← Demo case fixture
│
├── tests/                      ← 320 pytest tests (0 failures)
│   ├── test_scam_categories.py
│   ├── test_identifier_extractor_v2.py
│   ├── test_apk_analyzer.py
│   ├── test_ssrf_guard.py
│   ├── test_phase_c_hierarchy.py
│   ├── test_phase_d_action_layer.py
│   └── ...36 test files total
│
└── docs/                       ← Full project documentation
    ├── ARCHITECTURE.md         ← System design deep-dive
    ├── API.md                  ← Complete API reference
    ├── DEPLOYMENT.md           ← Deploy to Vercel + VPS + Docker
    └── SECURITY.md             ← Security model + privacy design
```

---

## 📡 API Reference

### Citizen API — No Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/parakh/analyze` | Analyze text message (SMS/WhatsApp/Hinglish) |
| `POST` | `/api/v1/parakh/url/analyze` | Analyze a suspicious URL |
| `POST` | `/api/v1/parakh/email/analyze` | Analyze raw `.eml` or email headers |
| `POST` | `/api/v1/parakh/qr/analyze` | Decode QR and analyze the payload URL |
| `POST` | `/api/v1/parakh/check-before-open` | Pre-click risk check (fast, cached) |
| `POST` | `/api/v1/parakh/report-to-police` | Forward to officer queue (consent-gated) |
| `GET` | `/api/v1/parakh/status/{report_id}` | Track status of a citizen-reported case |

### Investigation API — Bearer Token Required

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/investigate/login` | Officer sign-in → bearer token |
| `POST` | `/api/v1/investigate/submit` | Analyze + persist as a case |
| `POST` | `/api/v1/investigate/apk/analyze` | Static APK analysis (upload, up to 60 MB) |
| `POST` | `/api/v1/investigate/website/analyze` | Guarded website fetch and scoring |
| `GET` | `/api/v1/investigate/cases` | Paginated + filtered case list |
| `GET` | `/api/v1/investigate/cases/{id}` | Full case detail |
| `PATCH` | `/api/v1/investigate/cases/{id}/status` | Update status + officer note |
| `GET` | `/api/v1/investigate/cases/{id}/linked` | Cases linked by shared identifiers |
| `GET` | `/api/v1/investigate/cases/{id}/similar` | Near-duplicate content (SimHash) |
| `GET` | `/api/v1/investigate/identifier/{value}/cases` | All cases sharing this identifier |
| `GET` | `/api/v1/investigate/heat-list` | Trending scam identifiers |
| `GET` | `/api/v1/investigate/campaigns` | Cluster cases into fraud campaigns |
| `GET` | `/api/v1/investigate/cases/{id}/report.html` | Print-ready HTML investigation report |
| `GET` | `/api/v1/investigate/export/cases.csv` | Bulk CSV export |
| `GET` | `/api/v1/health` | System health + per-analyser status |

> **Full interactive docs:** `http://localhost:8000/docs` after starting the app.

---

## 🔒 Privacy & Security Design

| Property | Mechanism |
|---|---|
| **Citizen Mode never persists** | `create_case()` never called from citizen routes; enforced by automated test |
| **SSRF guard at every hop** | Every outbound URL checked against RFC-1918, loopback, link-local — at every redirect |
| **APK analysis is offline** | Static only — no APK executed, no Android SDK, no emulator |
| **Website analysis is guarded** | 2 MB stream cap, 10s timeout, 3 max redirects, no JS execution |
| **AI Fusion Guardrail** | Gemini AI can only raise a rule verdict, never silently lower a HIGH finding |
| **Known-site whitelist** | Government and official domains whitelisted from brand-lookalike scoring |
| **Passwords: scrypt** | `hashlib.scrypt` — no native-wheel dependency |
| **Tokens: SHA-256 hashed** | Only `SHA-256(token)` stored; raw token never persisted |
| **Reports: HTML-escaped** | `html.escape()` on all user-supplied fields — `<script>` in scam content can't execute |
| **Foreign keys enforced** | SQLite `PRAGMA foreign_keys=ON` — cascade deletes work correctly |
| **Officer jurisdiction scoping** | Officers can only access cases within their assigned unit/district |
| **Full audit trail** | Every case view, status change, and export logged with officer ID + timestamp |
| **MFA (optional)** | TOTP (`pyotp`) for Supervisor and Admin accounts |

---

## ☁️ Deployment

### Option 1 — Vercel (Citizen Mode + API)

```bash
npm install -g vercel
vercel

# Set in Vercel dashboard:
GEMINI_API_KEY=your_key
ENVIRONMENT=production
ALLOWED_ORIGINS=https://your-app.vercel.app
```

> **Note:** Vercel is ideal for the stateless Citizen Mode. Investigation Mode (persistent SQLite + 60 MB APK uploads) needs a persistent host.

### Option 2 — Persistent Host (Full Platform)

```bash
# Any Linux VPS, Railway, Render, or team laptop
git clone https://github.com/YaduvanshiHimanshunfsu/PARAKH.git
cd PARAKH
python run.py
```

### Option 3 — PostgreSQL for Production

Change one line in `.env`:
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/parakh
```
No code changes needed — SQLAlchemy handles the rest.

---

## ✅ PS01 Compliance

| PS01 Requirement | ✅ PARAKH Implementation |
|---|---|
| Analyze message/URL → risk level + reasons | `/parakh/analyze` + `/parakh/url/analyze` — Low/Medium/High + per-finding explanations |
| Analyze APK **or** website with identifier extraction | APK static analysis (permissions, manifest, certs) **AND** website analysis — **both** |
| Extract UPI IDs, phone numbers, URLs | 14 identifier types including UPI, phone, URLs, domains, bank accounts, crypto wallets |
| Searchable case history + downloadable report | Officer console: search, filter, identifier pivot, JSON/HTML/CSV export |
| Cross-source identifier linking | Weighted linking across all artifact types |
| Heat-list of trending scam identifiers | 7-day trend arrows, ranked by case count and recency |

---

## 🔭 Future Enhancements

| Feature | Status | Description |
|---|---|---|
| **Browser extension** | 🔜 Planned | Manifest V3, calls `/check-before-open`, warns before navigation |
| **Telegram bot** | 🔜 Planned | Forward a message → instant risk verdict |
| **WhatsApp bot** | 🔜 Planned | Business API integration for direct citizen reporting |
| **Playwright scraping** | 🔜 Planned | JS-rendered fraud sites (currently limited by no-JS constraint) |
| **Alembic migrations** | 🔜 Planned | Schema versioning for production deployments |
| **Redis rate limiting** | 🔜 Planned | Distributed limits for multi-instance deployment |
| **Automated takedown** | 💡 Concept | RDAP/registrar API integration to flag and request domain suspension |
| **ML classifier** | 💡 Concept | Transformer-based Hinglish classifier to supplement rules |
| **Inter-state intelligence sharing** | 💡 Concept | Federated identifier graph across state police portals |

---

## ⚠️ Known Limitations

| Limitation | Consequence |
|---|---|
| SQLite single-writer | Not suitable for high concurrent write load → swap to PostgreSQL for production |
| Static APK analysis only | Highly obfuscated/packed APKs may reveal less; dynamic sandboxing is out of scope |
| AI optional | Gemini used for enrichment; full rule fallback covers all artifact types |
| JS-rendered websites | Sites requiring JavaScript return thin HTML; stated in analysis output |
| RDAP coverage | Some registrars don't publish RDAP; domain age may read as "unknown" |
| Windows asyncio | 6 tests skipped on Windows (asyncio self-pipe); they pass on Linux/macOS |

---

## 📈 Measured Results

Measured on a **held-out test split** (30% by hash of item id, never used for
tuning) of a 450-item golden dataset. Reproduce with `python scripts/evaluate.py`;
the report is committed at [`eval/report.md`](eval/report.md).

| Metric | Before | **After** | Target | |
|---|---|---|---|---|
| SCAM precision | 0.75 | **1.00** | 0.92 | ✅ |
| Risky recall | 0.625 | **0.979** | — | ✅ |
| Hindi / Hinglish recall | 0.368 | **1.00** | 0.85 | ✅ |
| Official-domain false positives | 9 | **0** | 0 | ✅ |
| Identifier extraction F1 | 0.884 | **0.98** | 0.90 | ✅ |
| APK detection accuracy | 1.00 | **1.00** | 0.90 | ✅ |
| 3-class macro F1 | 0.37 | **0.649** | 0.85 | ❌ |

**We report the miss rather than hide it.** Macro-F1 falls short because the
middle `SUSPICIOUS` class is only 12 test items and is intrinsically fuzzy.
SCAM and SAFE — the two classes that drive real decisions — are both
near-perfect.

Weights and both verdict thresholds are fitted on a **development** split by
`scripts/fit_rule_weights.py` and committed as data. The test split exists to
tell us the truth, not to tune against.

---

## 🧪 Running Tests

```bash
# Activate virtual environment
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

# Run the full backend test suite
pytest

# Expected: 541 passed, 6 skipped (Windows asyncio), 0 failed

# Run specific test groups
pytest tests/test_scam_categories.py -v
pytest tests/test_ssrf_guard.py -v
pytest tests/test_phase_c_hierarchy.py -v      # hierarchy, scoping, audit chain
pytest tests/test_phase_d_action_layer.py -v  # action pack and approval chain
```

```bash
# Accuracy on the golden dataset, and the honesty gate
python scripts/evaluate.py
python scripts/check_ui_claims.py

# Frontend: 67 unit tests, 84 browser tests (desktop 1440px + mobile 390px)
cd frontend && npx vitest run && npx playwright test
```

The browser suite includes an assertion that **no request ever leaves the
local origin** — the demo must work with Wi-Fi switched off.

---

## 🏁 Conclusion

PARAKH is not just a scam detector — it is a **fraud intelligence platform** designed around the real workflow of a police investigation.

| Traditional Approach | PARAKH |
|---|---|
| Analyze one artifact at a time | 6 artifact types in one platform |
| Return verdict, then forget | Searchable case history that grows over time |
| Miss connections between fraud artifacts | **Auto-link cases via shared identifiers** |
| Fail when AI is down | Full offline rule-based fallback for every artifact type |
| Privacy vs. investigation — pick one | **Dual-mode:** citizen privacy + officer intelligence |
| Officers see only their FIRs | Campaign view reveals the full fraud network |

**In a live demo, PARAKH can show:** an SMS, an APK, and a fraudulent website — submitted separately — automatically resolved into **one fraud campaign**, with the shared UPI ID at the top of the heat-list, all three cases linked by the identifier graph, and a print-ready investigation report generated in under a second.

That is the fragmentation problem PS01 describes. That is what PARAKH solves.

---

<div align="center">

**Built with ❤️ for Rajasthan Police Hackathon 2026**

**Team Gravity** — Himanshu Yadav · Gaurav Raj · Umesh Gupta

National Forensic Sciences University (NFSU)

*PARAKH — परख | परखो, फिर भरोसो*

</div>
