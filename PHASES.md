# Phase Plan — PARAKH → Rajasthan Police PS01

**Target problem statement:** PS01 — *Scam Message & Phishing Link Detection with Fake Loan / Investment App and Fraudulent Website Analysis* (Cyber Fraud / Phishing / Malicious Apps).

**Document purpose:** A phase-wise conversion plan from the current PARAKH codebase to a PS01-compliant platform. Each phase states a goal, sub-phases, the real files touched, exit criteria, and risks.

---

## Phase 0 — Starting Position & Decisions ✅ COMPLETE

> **Verified 2026-11-18.** Baseline measured by execution, not inspection: **31 passed, 6 skipped, 0 failed**; app boots; live fallback analysis confirmed working. Four defects found (B-1…B-4) and all three design tensions resolved — see **[DECISIONS.md](DECISIONS.md)** for the full record, including the demo-blocking invalid `GEMINI_API_KEY` (B-1).

### What the current codebase already does well

| Capability | Where | Reuse value |
|---|---|---|
| SMS / WhatsApp / social text classification | `app/services/scam_analyzer.py`, `app/prompts.py` | **High** — 11 scam categories, 8 manipulation tactics, strict Pydantic-validated Gemini output, red-flag phrases verified against source text |
| Email + raw `.eml` analysis | `app/services/email_analyzer.py` | **High** — SPF/DKIM/DMARC, header alignment, attachment risk, deterministic scoring fused with AI |
| URL structural risk | `app/services/url_intelligence.py` | **Medium-High** — 9 signals (`NO_HTTPS`, `IDN_OR_PUNYCODE`, `URL_SHORTENER`, `HIGH_RISK_TLD`, `UNUSUALLY_LONG_URL`, `DEEP_SUBDOMAIN_CHAIN`, `ENCODED_URL_CONTENT`, `CREDENTIAL_OR_KYC_LURE`, `BRAND_LIKE_DOMAIN`) + TLS probe + VirusTotal/Web Risk |
| Offline rule fallback | `app/services/fallback_analyzer.py`, `app/data/scam_rules.py` | **High** — 17 explainable regex rules; works with zero AI availability |
| Explainable output contract | `app/schemas.py` | **High** — verdict + confidence + severity + per-signal explanation already modelled |
| Security posture | `app/core/middleware.py`, `rate_limiter.py`, `provider_guard.py` | **High** — CSP, HSTS, size limits, hybrid rate limiting, AI concurrency gate |
| PDF report generation | `frontend/src/lib/report.js`, `redaction.js` | **Medium** — dependency-free generator, but client-side only |

### What PS01 requires that does not exist at all

| PS01 requirement | Status | Phase |
|---|---|---|
| Android APK analysis (permissions, embedded URLs/IPs, package metadata, signatures, icons) | **Absent** | Phase 3 |
| Website content analysis (Ponzi/MLM/betting language, hosting details) | **Absent** — `url_intelligence.py` deliberately never fetches page content | Phase 4 |
| Identifier extraction (UPI IDs, bank details, phone numbers, crypto wallets) | **Absent** | Phase 2 |
| Domain age, redirect chain, blacklist matching | **Absent** — current code *refuses* redirects by design | Phase 2 |
| Server-side case storage + search | **Absent** — zero persistence by design | Phase 1, 5 |
| Cross-source identifier linking | **Absent** | Phase 5 |
| Repeat-content / similarity detection | **Absent** | Phase 5 |
| Investigation dashboard | **Absent** | Phase 6 |
| Heat-list of trending scam identifiers | **Absent** | Phase 5, 6 |
| Officer vs citizen roles | **Absent** | Phase 1 |

### Design tensions — all resolved

Recorded as ADRs in **[DECISIONS.md](DECISIONS.md)**:

| ADR | Tension | Resolution |
|---|---|---|
| **001** | Privacy-first storage vs. searchable police records | **Dual-mode** — Citizen (ephemeral, unchanged) + Investigation (persisted); crossing requires explicit opt-in |
| **002** | `url_intelligence.py` never fetches content vs. PS01 website analysis | **Separate guarded fetcher** with SSRF checks at every redirect hop; citizen no-fetch guarantee stays literally true |
| **003** | Vercel serverless vs. durable storage + 5–60 MB APKs | **SQLite + async SQLAlchemy, persistent host** (laptop/VPS), ORM-only so Postgres is a connection-string swap |
| **004** | Global 3.25 MB request cap vs. APK size | **Per-route limit** — APK route exempted; global cap unchanged to avoid widening the DoS surface |
| **005** | AI-first vs. deterministic new analysers | **Deterministic-first** — APK and website verdicts never depend on Gemini availability |

### Defects found during baseline verification

| # | Finding | Severity |
|---|---|---|
| **B-1** | OS-level `GEMINI_API_KEY` returns HTTP 401; app reports `provider_configured: true` then wastes **1113 ms** on 3 dead model attempts per request. `.env` cannot override it — OS env vars outrank dotenv in pydantic-settings. | **Demo-blocking** |
| **B-2** | `CREDENTIAL_OR_KYC_LURE` matches `path + query` only (`url_intelligence.py:336`). `sbi-verify-kyc.in` has *verify* and *kyc* in the **host** and scores nothing — rated MEDIUM/33 instead of HIGH. | High |
| **B-3** | No identifier extraction, confirmed empirically — phone `9876543210` in the test message was not captured anywhere. | Expected (Phase 2.1) |
| **B-4** | 6 tests never run on Windows (asyncio self-pipe). Security-headers and both provider contract tests are unverified locally. | Medium |

### Phase 0 artifacts produced

- `DECISIONS.md` — 5 ADRs, verified baseline, 4 defects, 5 open items (O-1…O-5)
- `.env` — created from template (was missing; gitignored)

---

## Phase 1 — Foundation, Pivot, and Persistence ✅ COMPLETE

> **Delivered.** Async SQLAlchemy case store, officer auth, and the unified submission pipeline are live. Suite: **93 passed, 6 skipped, 0 failed**. The ADR-001 guarantee is enforced by `test_citizen_mode_analysis_persists_nothing`.
>
> **Built:** `app/db/{__init__,models,session,seed}.py` · `app/core/auth.py` · `app/services/case_service.py` · `app/utils/fingerprint.py` · `app/api/investigate.py` · 7 new settings in `config.py` · schema layer in `schemas.py`
>
> **Endpoints:** `POST /investigate/auth/login` · `POST /investigate/auth/logout` · `GET /investigate/me` · `POST /investigate/submit` · `GET /investigate/cases` · `GET /investigate/cases/{id}` · `PATCH /investigate/cases/{id}`
>
> **Decisions made during build:** `hashlib.scrypt` replaced `passlib[bcrypt]` (zero dependencies, no native-wheel risk on Python 3.14). `greenlet` added — SQLAlchemy's asyncio support needs it and does not install it automatically. Tables are created with `create_all`, not Alembic: the schema is recreated between demos and migration tooling earns nothing in a 24-hour build.
>
> **Bug found and fixed:** `get_session(request)` without a `Request` annotation made FastAPI treat `request` as a query parameter, returning 422 on every investigation route. All 18 integration tests failed identically until it was annotated.

**Goal:** Turn a stateless citizen tool into a platform with durable cases, roles, and a unified submission pipeline — without breaking anything that already works.

**PS01 coverage:** Enables "maintain searchable records and evidence reports" (prerequisite for Phases 5–6).

### 1.1 Deployment & storage decision
- Decide: persistent host + Postgres/Turso, **or** local-only demo with SQLite. Record the decision in the README.
- If staying on Vercel for the citizen frontend, split: static SPA + citizen API on Vercel, investigation API on a persistent host.
- Raise `max_request_bytes` for the APK route specifically (per-route limit, not global) — see sub-phase 3.1.

### 1.2 Data layer
- Add SQLAlchemy 2.0 (async) + `aiosqlite` (dev) / `asyncpg` (prod).
- New: `app/db/session.py`, `app/db/models.py`, `app/db/__init__.py`.
- Core tables:
  - `cases` — id, public case_id, artifact_type (`MESSAGE|URL|EMAIL|APK|WEBSITE`), risk_level, risk_score, verdict, created_at, submitted_by, status (`NEW|UNDER_REVIEW|CLOSED`), source (`CITIZEN|OFFICER`), notes
  - `artifacts` — case_id FK, raw content (text) / file sha256, content_hash, simhash
  - `findings` — case_id FK, code, severity, explanation, evidence_snippet (one row per triggered indicator — this is what makes risk *explainable* and queryable)
  - `identifiers` — case_id FK, type (`PHONE|UPI|DOMAIN|URL|EMAIL|IFSC|BANK_ACCOUNT|CRYPTO_BTC|CRYPTO_ETH|PACKAGE|TELEGRAM|IP`), value_normalized, value_raw, first_seen, context
  - `users` — id, username, password_hash, role (`CITIZEN|OFFICER|ADMIN`)
- Index `identifiers(type, value_normalized)` and `cases(created_at)` — the heat-list and linking queries depend on it.

### 1.3 Unified submission pipeline
- New: `app/services/case_service.py` — single entry point every analyser feeds into: `create_case(artifact, analysis_result, identifiers, findings) -> Case`.
- Refactor so `scam_analyzer`, `email_analyzer`, `url_intelligence` all emit a common `AnalysisBundle` (verdict, score, findings[], identifiers[]) that `case_service` persists.
- Keep the existing endpoints returning their current response shape; add `?persist=true` or a separate `/investigate/*` route group so citizen mode stays ephemeral.

### 1.4 Minimal auth and roles
- New: `app/core/auth.py` — bearer token or session cookie, `passlib[bcrypt]` hashing.
- Citizens may submit anonymously. Officer endpoints (`/api/v1/investigate/*`, dashboard) require `OFFICER` or `ADMIN`.
- Seed one officer account via an env-driven bootstrap script. Do not build user self-registration.

### 1.5 Schema extensions
- Extend `app/schemas.py`: `RiskLevel` (`LOW|MEDIUM|HIGH`) alongside existing `Verdict`; `Identifier`, `Finding`, `CaseSummary`, `CaseDetail`, `SubmissionRequest`.
- Note: PS01 asks for Low/Medium/High. The existing `Severity` enum already uses these values — map `Verdict`+`confidence` → `RiskLevel` in one place so the mapping is auditable.

**New dependencies:** `sqlalchemy>=2.0`, `aiosqlite`, `asyncpg` (prod), `passlib[bcrypt]`

**Exit criteria**
- A message submitted through the new pipeline is persisted with its findings and extracted identifiers, and retrievable by case ID.
- Officer login works; unauthenticated access to `/investigate/*` returns 401.
- All 11 existing test files still pass.

**Estimated effort:** 6–8 hours
**Risk:** Scope creep into a full user-management system. Keep auth deliberately thin.

---

## Phase 2 — Message & URL Analysis Upgrade ✅ COMPLETE

> **Delivered.** All six sub-phases. **31 dedicated extractor tests + 13 fingerprint tests**, all passing.
>
> **Built:** `app/services/identifier_extractor.py` (14 identifier types, span-based overlap resolution) · `app/services/url_enrichment.py` (RDAP domain age with DB cache, SSRF-guarded hop-by-hop redirects, blacklist matching) · `app/services/artifact_analyzer.py` (the analyser → `AnalysisBundle` seam) · `app/data/blacklists.py` · 10 new rules in `scam_rules.py`
>
> **New scam categories:** `LOAN_APP_FRAUD`, `PONZI_MLM`, `BETTING_GAMBLING`, `UTILITY_BILL_SCAM` — added to the enum, the rule packs, **and** the Gemini prompt. Verified classifying correctly through the offline fallback with no API key.
>
> **B-2 fixed:** new `CREDENTIAL_OR_KYC_DOMAIN` signal inspects the registered domain, not just the path. `sbi-verify-kyc.in/urgent` moved **MEDIUM/33 → HIGH/57**; `hdfc-kyc-update.xyz/login` → CRITICAL/84; `google.com` stays LOW/0.
>
> **Extractor bugs found by testing, not review:**
> - Phone lookahead `(?![\d@.])` rejected any number ending a sentence — `"call 9876543210."` extracted nothing. Narrowed to `(?!\.\d)`.
> - An IP-hosted URL yielded a `DOMAIN` identifier instead of `IP`.
> - Telegram links lost the overlap tie to the generic URL pattern, so `t.me/...` was reported as a plain link. Telegram now outranks URL — for an investigator the handle *is* the identifier.
> - Dotted quads in version strings were extracted as IPs.
>
> **Verified end-to-end:** three messages (KYC phishing, Ponzi, loan app) → three HIGH-risk cases, with cross-case search on a shared phone number returning both cases that contain it. That is the PS01 linking premise already working.

**Goal:** Close the gap between the current URL/message analysis and PS01's explicit checklist, and build the identifier-extraction engine that every later phase depends on.

**PS01 coverage:** "Message and URL analysis" — *fully*. "Explainable risk assessment" — *strengthened*.

### 2.1 Identifier extraction engine (highest-leverage single module)
- New: `app/services/identifier_extractor.py` — shared by messages, emails, APKs, and websites.
- Patterns to implement, each with normalization:
  - Indian phone: `(?:\+?91[\-\s]?)?[6-9]\d{9}` → normalize to E.164
  - UPI ID: `[\w.\-]{2,64}@[a-zA-Z]{2,32}` filtered against a known PSP-handle list (`okaxis`, `ybl`, `paytm`, `upi`, `ibl`, `axl`, …) to avoid matching every email
  - IFSC: `[A-Z]{4}0[A-Z0-9]{6}`
  - Bank account: 9–18 digit runs with contextual keywords nearby
  - BTC: `\b(?:bc1[a-z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b`
  - ETH/USDT-ERC20: `0x[a-fA-F0-9]{40}`
  - Telegram: `t\.me/\S+`, `@[a-zA-Z0-9_]{5,32}`
  - Android package: `[a-z][a-z0-9_]*(?:\.[a-z0-9_]+){2,}`
  - Domains/URLs: reuse `UrlIntelligenceService.extract_urls`
- Return `list[Identifier]` with type, raw value, normalized value, and surrounding context snippet (context is what makes a report investigation-ready).
- Unit-test each pattern against both positives and near-miss negatives. False-positive UPI/bank matches will pollute the heat-list if this is sloppy.

### 2.2 Domain age via RDAP
- Add to `url_intelligence.py`: `_domain_age()` using RDAP over the existing `httpx` client (`https://rdap.org/domain/{registered_domain}`) — returns JSON, no WHOIS parsing, no new dependency.
- New signal `NEWLY_REGISTERED_DOMAIN` (HIGH if < 30 days, MEDIUM if < 180 days). Newly-registered is one of the strongest phishing indicators and PS01 names it explicitly.
- Cache results in the DB to avoid repeat lookups during a demo.

### 2.3 Redirect chain resolution
- New method `resolve_redirect_chain()` — HEAD requests, `follow_redirects=False`, manual hop loop, max 5 hops, 3s total timeout, reusing the existing `_public_addresses()` SSRF guard at **every** hop.
- New signals: `REDIRECT_CHAIN_LONG`, `CROSS_DOMAIN_REDIRECT`, `SHORTENER_RESOLVED_TO_RISKY_DOMAIN`.
- Record the full chain in `findings` — a redirect chain is itself evidence.

### 2.4 Blacklist matching
- New: `app/data/blacklists.py` + a `blacklist_entries` table seeded from the R4C sample dataset and any public feeds used.
- Match on registered domain, full URL, phone, UPI ID, and package name.
- New signal `BLACKLIST_MATCH` (HIGH). Keep the source of each entry recorded so a match is explainable, not a black box.

### 2.5 New scam-rule packs
- Extend `app/data/scam_rules.py` with rule groups the current set lacks:
  - **Instant-loan app lures** — "loan in 5 minutes", "no documents", "instant approval", "Aadhaar only", app-download pressure
  - **Ponzi / MLM** — "referral bonus", "level income", "downline", "binary plan", "joining fee", "team commission"
  - **Betting / gambling** — "betting ID", "fancy rate", "Teer result", "colour prediction", "100% winning tips"
  - **Electricity bill** — "electricity will be disconnected tonight", "update meter", a very common Indian vector named in PS01's background
  - **Parcel / customs** — already partly covered; strengthen
- Each rule keeps the existing `ScamSignalRule` shape so the fallback analyser picks them up for free.

### 2.6 Relax over-strict URL refusals for investigation mode
- `_normalise()` currently *rejects* direct-IP links, non-standard ports, and embedded credentials. For a citizen that is correct; for an investigator those are **findings, not errors**.
- In investigation mode, convert each refusal into a HIGH-severity signal (`DIRECT_IP_HOST`, `NON_STANDARD_PORT`, `EMBEDDED_CREDENTIALS`) and continue the analysis.

**Exit criteria**
- Submitting a scam SMS returns risk level + reasons **and** extracted phone numbers, UPI IDs, and URLs.
- A shortened URL resolves its chain and reports the final destination's domain age.
- A blacklisted domain produces a `BLACKLIST_MATCH` finding citing its source.

**Estimated effort:** 8–10 hours
**Risk:** RDAP rate limits and occasional non-responses — cache aggressively and degrade to `UNKNOWN` rather than failing the analysis.

---

## Phase 3 — Android APK Analysis ✅ COMPLETE

> **Delivered.** All six sub-phases. **32 dedicated APK tests + 7 upload-route tests**, all passing. Suite now **131 passed, 6 skipped, 0 failed**.
>
> **Built:** `app/services/apk_parsing.py` (container validation, manifest, certificates, DEX strings, icon dHash) · `app/services/apk_analyzer.py` (risk aggregation) · `app/data/apk_permission_rules.py` (14 single-permission rules + 6 combination rules) · `POST /investigate/apk/analyze` · `tests/apk_fixtures.py`
>
> **Verified separation:** a synthetic predatory loan app scores **HIGH / 100** with 20 findings; a benign notes app scores **LOW / 25**. Fully deterministic — re-running gives identical results, and `test_analysis_needs_no_ai_provider` proves a verdict survives a missing API key.
>
> **Dependency decisions:**
> - **`pyaxmlparser`, not `androguard`** — androguard is far heavier and slower, and nothing here needs DEX disassembly. Manifest parsing is wrapped so an `ImportError` degrades to a stated limitation instead of failing the analysis.
> - **`imagehash` installed, then removed.** It pulls scipy + numpy + PyWavelets (~50 MB) for one function. dHash is 15 lines on Pillow, which was already a dependency.
>
> **Testing without the Android SDK:** `tests/apk_fixtures.py` *encodes real binary AndroidManifest.xml* — string pool, resource map, and element chunks — so fixtures are deterministic and no binary sample of unknown provenance enters the repo. Confirmed round-trip: `pyaxmlparser` decodes package, label, version, SDK levels, permissions, and activities from the generated manifest.
>
> **Bug found during build:** `APK(io.BytesIO(data), raw=True)` is wrong — `raw=True` expects `bytes`, not a file object. Caught by reading the constructor source rather than at runtime, since the surrounding `except Exception` would have silently degraded every manifest to "unreadable".
>
> **Cross-artifact linking proven:** `test_apk_case_links_to_a_message_sharing_the_same_host` uploads an APK with an embedded C2 host, submits an SMS citing the same host, and asserts one search returns **both** cases. That is PS01's core premise working across artifact types.

**Goal:** Build the module that does not exist today and that most differentiates a PS01 submission. Static analysis only — dynamic sandboxing is explicitly out of scope.

**PS01 coverage:** "Android app analysis" — the single hardest Must-Have.

### 3.1 Upload boundary
- New route `POST /api/v1/investigate/apk/analyze` with its own size ceiling (~60 MB), bypassing the global 3.25 MB middleware limit via a per-route check.
- Reuse the pattern in `app/services/media_validation.py`: verify magic bytes (`PK\x03\x04`), confirm `AndroidManifest.xml` and `classes.dex` exist in the zip, reject zip bombs by checking the uncompressed-size ratio before extracting anything.
- Process in a temp directory, delete on completion. Never execute, never install.

### 3.2 Manifest and metadata extraction
- New: `app/services/apk_analyzer.py` using `pyaxmlparser` (lightweight, manifest-focused) as primary.
- Extract: package name, app label, versionName/versionCode, minSdk/targetSdk, permissions, exported activities/services/receivers, declared SDKs.
- `androguard` optional for deeper DEX work — it is heavy and slow; do not make the demo depend on it.

### 3.3 Permission risk model
- New: `app/data/apk_permission_rules.py`.
- Score **individual** dangerous permissions and, more importantly, **combinations**. A flashlight or loan app requesting `READ_SMS` + `READ_CONTACTS` + `INTERNET` is the classic predatory-loan signature PS01 describes.
- Rules to encode:
  - `READ_SMS` / `RECEIVE_SMS` — OTP interception (CRITICAL in a finance app)
  - `READ_CONTACTS` + `INTERNET` — contact harvesting for harassment-based recovery
  - `CAMERA` + `READ_EXTERNAL_STORAGE` — document/selfie exfiltration
  - `READ_CALL_LOG`, `ACCESS_FINE_LOCATION`, `SYSTEM_ALERT_WINDOW` (overlay attacks), `BIND_ACCESSIBILITY_SERVICE` (the remote-control red flag)
  - `REQUEST_INSTALL_PACKAGES` — dropper behaviour
- Output one `Finding` per triggered rule, with plain-language explanation. This is how the APK path stays *explainable* like the rest of the app.

### 3.4 Embedded URL / IP / identifier extraction
- Scan `classes*.dex` strings, `resources.arsc`, `res/raw/`, and `assets/` for printable strings.
- Pipe every extracted string through the Phase 2 `identifier_extractor` — this is why that module is built first.
- Feed discovered URLs back through `url_intelligence` so an APK's C2/payment endpoints get domain-age and blacklist treatment automatically.

### 3.5 Signature and icon comparison
- Parse `META-INF/*.RSA|DSA|EC` for the signing certificate: subject, issuer, SHA-256 fingerprint, validity window.
- Flag: self-signed with debug-certificate subject (`CN=Android Debug`), validity under 1 year, and fingerprints reused across different package names (strong campaign-linking signal).
- Extract the launcher icon, compute a perceptual hash (`imagehash` + the already-present `Pillow`), and compare against hashes of legitimate bank/finance app icons to detect visual impersonation.
- Store `cert_sha256` and `icon_phash` as identifiers so Phase 5 can link apps across cases.

### 3.6 APK risk aggregation
- Combine permission score + embedded-URL risk + certificate anomalies + package-name similarity to known brands into one Low/Medium/High with the triggering indicators listed.
- Keep this **fully deterministic** — no Gemini dependency. If the AI provider is down mid-demo, APK analysis must still work.

**New dependencies:** `pyaxmlparser`, `imagehash` (`androguard` optional)

**Exit criteria**
- Uploading a sample APK returns package metadata, a permission risk breakdown, embedded URLs/IPs, certificate details, and a Low/Medium/High verdict with named indicators.
- Extracted URLs and phone numbers appear as linked identifiers on the case.
- Works with the Gemini key removed from the environment.

**Estimated effort:** 10–14 hours — **the largest single phase**
**Risk:** Obfuscated/packed APKs yield few readable strings. Mitigate by stating this limitation in the report output rather than returning an empty or misleading result.

---

## Phase 4 — Website Content Analysis ✅ COMPLETE

> **Delivered.** All five sub-phases. **30 dedicated tests**, all passing.
>
> **Built:** `app/services/website_analyzer.py` (guarded fetcher + content scoring) · `app/data/website_rules.py` (17 rules + legitimacy markers) · `POST /investigate/website/analyze`
>
> **Fetch safety** — SSRF guard re-applied at every redirect hop, 2 MB streamed cap aborted mid-download, 10s timeout, max 3 redirects, HTML/text content types only, no JS execution, neutral User-Agent that leaks nothing about the operator. Limits are module constants, not settings: they are safety boundaries, not tuning knobs.
>
> **Rule coverage:** guaranteed/daily returns, referral-chain & MLM structure, joining-package fees, betting platforms and prediction games, sure-win tips, instant-loan-no-checks, direct APK distribution, fake SEBI/RBI approval claims, Telegram funnels, crypto deposit requests.
>
> **Absence as signal:** on a page that solicits money, missing privacy policy / terms / contact / registration details raises `MISSING_LEGITIMACY_MARKERS`. A legitimate business page with those disclosures scores LOW — verified by test.
>
> **Verified:** a Ponzi page scores **HIGH / 100** and yields the full money trail (UPI, bank account, IFSC, phone, Telegram) including UPI deep links from `<a href="upi://pay?pa=...">`. A genuine stationery-shop page scores **LOW**.
>
> **Honest limitation:** a JS-rendered page returns little text. Rather than letting that look clean, thin content raises an explicit limitation in the output.

**Goal:** Analyse what a fraudulent investment, Ponzi, MLM, or betting site actually *says* and *collects* — not just its URL shape.

**PS01 coverage:** "Website analysis" (the second Must-Have alternative alongside APK).

### 4.1 Guarded fetcher
- New: `app/services/website_analyzer.py`.
- Hard constraints: `httpx` with a 10s total timeout, 2 MB response cap (streamed, aborted on exceed), max 3 redirects, **SSRF guard reusing `_public_addresses()` on every hop**, no JavaScript execution, a neutral generic User-Agent, HTML/text content types only.
- Never fetch in citizen mode without an explicit user action. Record fetch time and final URL as evidence.

### 4.2 Content extraction
- `BeautifulSoup` (already a dependency) → visible text, `<title>`, meta description, all `<a href>`, all `<form action>` + input field names, `<script src>` origins, and any embedded images of QR codes.
- Capture a text snapshot into `artifacts` as the evidence snapshot PS01 asks for. (Full-page screenshots via Playwright are a stretch goal — Playwright is already a frontend devDependency, but adding it server-side is heavy.)

### 4.3 Ponzi / MLM / betting scoring
- New: `app/data/website_rules.py`, mirroring the `ScamSignalRule` shape for consistency.
- **Guaranteed-returns:** "assured returns", "100% safe", "double your money", "daily profit", "ROI", fixed-percentage-per-day claims
- **MLM / referral chain:** "referral bonus", "downline", "level income", "binary plan", "matrix", "joining package", "team commission"
- **Betting:** "betting ID", "deposit bonus", "colour prediction", "fancy rate", "instant withdrawal", "welcome bonus"
- **Loan:** "instant loan", "no CIBIL", "Aadhaar only", "approval in 5 minutes", APK download links on a non-Play-Store domain
- **Absent-legitimacy markers:** no registered address, no SEBI/RBI registration number, no about/contact page, no privacy policy — the *absence* of these is itself a Medium signal for a financial site.

### 4.4 Identifier harvesting from page content
- Run the Phase 2 extractor across the full page text: UPI IDs, bank account + IFSC pairs, phone/WhatsApp numbers, Telegram links, crypto wallet addresses.
- Decode any on-page QR images (`Pillow` + a QR decode library) to catch UPI payment QRs — a common pattern on these sites.
- These identifiers are the highest-value output for police: they are the money trail.

### 4.5 Hosting and domain intelligence
- Resolve IP(s), reverse-DNS, ASN/hosting provider (free IP-to-ASN API or a local dataset).
- Reuse Phase 2 RDAP for registrar, creation date, and name servers.
- Flag shared hosting IPs that also serve other cases already in the DB — a direct campaign-linking signal that feeds Phase 5.

**New dependencies:** a QR decode library (e.g. `pyzbar` or `opencv-python-headless`) — optional, degrade gracefully if unavailable

**Exit criteria**
- Submitting a Ponzi/betting site URL returns: risk level, the specific promotional phrases that triggered it, all extracted payment identifiers, hosting details, and a stored text snapshot.
- SSRF attempts against `127.0.0.1`, `169.254.169.254`, and private ranges are blocked at every redirect hop — add explicit tests for this.

**Estimated effort:** 8–10 hours
**Risk:** Many fraud sites are JS-rendered and return near-empty HTML to a plain fetch. State this limitation in output; optionally add Playwright rendering as a stretch goal.

---

## Phase 5 — Identifier Graph, Linking & Similarity ✅ COMPLETE

> **Delivered.** All five sub-phases. **20 dedicated tests**. Suite now **211 passed, 6 skipped, 0 failed**.
>
> **Built:** `app/services/link_service.py` · endpoints `GET /cases/{id}/linked`, `GET /cases/{id}/similar`, `GET /identifiers/{type}/cases`, `GET /heatlist`, and the citizen-facing `POST /PARAKH/check-before-open`.
>
> **Weighted linking:** a shared UPI ID, bank account, crypto wallet or signing certificate scores 10; a shared URL scores 3. Without weighting, two unrelated messages citing `bit.ly` would rank as high as two sharing a collection account. Verified by test: a case sharing a UPI ID ranks above one sharing only a domain.
>
> **Similarity bug found and fixed.** The implementation used **word** 5-gram shingles while its own docstring said **character** 5-grams. Measured on real scam text, word shingles gave: one word swapped = 12 bits, two words swapped = **34** — against unrelated messages at **35**. Near-duplicates were indistinguishable from noise. Switching to character n-grams gave clean separation (variants 8–14, unrelated 26+), and the threshold is now 16 with a 10-bit margin. Both ends of that separation are pinned by parametrised tests.
>
> **Verified end-to-end:** an SMS, an APK and a website all citing `fraudster@ybl` surface as one campaign — APK linked to both messages, exact-template match detected between two SMS variants (distance 0), identifier pivot returning all three cases across two artifact types, and the heat-list ranking the shared UPI ID at the top.
>
> **Pre-click warning** is deliberately anonymous and cheap — indexed identifier lookup plus blacklist check, no fetching and no AI — so a browser extension or bot can call it inline.

**Goal:** Deliver the intelligence layer that makes this a *platform* rather than four separate scanners — exactly the fragmentation PS01's background section complains about.

**PS01 coverage:** "Linked domains, apps, phone numbers and payment identifiers", "repeat-content and similarity detection", "heat-list" (two Good-to-Haves + a Must-Have dashboard component).

### 5.1 Cross-source identifier linking
- New: `app/services/link_service.py`.
- Query: given an identifier, return every case it appears in, across all artifact types.
- Query: given a case, return sibling cases sharing ≥1 identifier, ranked by how many and how rare the shared identifiers are (a shared phone number is far more significant than a shared `bit.ly` domain).
- This directly answers PS01's core premise: *"These threats often reuse the same domains, app identifiers, phone numbers and payment accounts, yet they are reported and examined separately."*

### 5.2 Repeat-content and near-duplicate detection
- Exact duplicates: SHA-256 of normalized text (lowercased, whitespace-collapsed, digits masked — so the same template with different amounts still matches).
- Near-duplicates: SimHash over character 5-grams, ~30 lines of code, no new dependency. Hamming distance ≤ 3 → near-duplicate.
- Store `content_hash` and `simhash` on `artifacts` at write time so detection is a cheap indexed lookup, not a scan.
- Surface as "This message matches 14 earlier reports" — campaign detection, visible in the dashboard.

### 5.3 Campaign clustering
- Group cases into campaigns via connected components over the shared-identifier graph (union-find over `identifiers`, run on demand — no graph database needed).
- Assign each cluster a label and show its size, date range, and dominant identifiers.

### 5.4 Heat-list aggregation
- New: `app/services/heatlist_service.py`.
- `GROUP BY (type, value_normalized)` with report count, distinct-case count, first-seen, last-seen, and a 7-day trend delta.
- Separate ranked lists for domains, phone numbers, UPI IDs, APK packages, and crypto wallets.
- Cache for 60s — this query runs on every dashboard load.

### 5.5 Pre-click warning API
- `POST /api/v1/check-before-open` — a fast, cached endpoint returning a Low/Medium/High verdict for a URL, backed by the blacklist + heat-list + cached prior analyses.
- Designed for sub-200ms response so the Phase 7 browser extension and bot can call it inline. PS01 asks the system to "warn users before they open a risky link".

**Exit criteria**
- A phone number appearing in an SMS, inside an APK, and on a website shows all three cases linked on one screen.
- Submitting a template message already in the DB reports the match count.
- The heat-list ranks the top domains/numbers/UPI IDs with counts and trend direction.

**Estimated effort:** 6–8 hours
**Risk:** Without Phase 2.1 normalization discipline, linking produces noise. Validate identifier quality before building the graph on top of it.

---

## Phase 6 — Investigation Dashboard & Reporting ✅ COMPLETE

> **Delivered.** All six sub-phases. **17 backend tests + 25 browser checks**, all passing.
>
> **Built (frontend):** `lib/investigateApi.js` · `app/OfficerAuthContext.jsx` · `app/InvestigateLayout.jsx` · `features/investigate/ui.jsx` · five pages (login, case list, case detail, identifier pivot, heat-list, new analysis) · routes wired into `AppRouter.jsx`
>
> **Built (backend):** `app/services/report_builder.py` · `GET /cases/{id}/report` (HTML, full or redacted) · `report.json` · `export/cases.csv` · `export/identifiers.csv` · `POST /PARAKH/report-to-police`
>
> **Verified in a real browser** (Playwright, Chromium, 1440×900): login gate, wrong-password handling, 14-case list, identifier search returning 4 cases across 3 artifact types, case detail with all panels, status and note updates, identifier pivot, heat-list, new-analysis submission, report export, and citizen pages still loading — **25/25 checks, zero console errors**.
>
> **Reports are print-optimised HTML, not a hand-rolled PDF.** A browser prints it with correct fonts, Devanagari support and page breaks — none of which a from-scratch PDF writer would get right in a hackathon. Analysed content is HTML-escaped, pinned by a test that submits `<script>` and asserts it cannot execute in the report.
>
> **Citizen opt-in (6.6)** is the single exception to ADR-001, and the consent gate is the whole safeguard. Three tests cover it: rejection without consent, *no rows written* without consent, and the original guarantee still holding for plain analysis.
>
> **Session storage choice:** the officer token lives in `sessionStorage`, not `localStorage` — an officer console should not survive a tab closing on a shared machine.

**Goal:** Give officers the searchable case history, linked-entity views, and downloadable evidence reports that PS01 names as a Must-Have.

**PS01 coverage:** "Investigation dashboard" (Must-Have), "Reporting and monitoring".

### 6.1 Routing and access control
- Extend `frontend/src/app/AppRouter.jsx` (currently 8 routes) with an officer-gated branch:
  - `/investigate` — case list
  - `/investigate/case/:caseId` — case detail
  - `/investigate/identifier/:type/:value` — everywhere this identifier appears
  - `/investigate/heatlist` — trending scam identifiers
  - `/investigate/submit` — officer submission (message / URL / APK / website)
  - `/login`
- Citizen routes (`/`, `/check`, `/result`, `/rescue`, `/evidence`, `/help`, `/learn`) remain untouched and unauthenticated.

### 6.2 Case list and search
- Filters: artifact type, risk level, date range, status, free-text across content and identifiers.
- Sort by date, risk score, or linked-case count.
- Server-side pagination — do not load the whole table.

### 6.3 Case detail view
- Panels: artifact preview → risk verdict with every triggered indicator and its explanation → extracted identifiers (each clickable to its identifier page) → linked cases → similar-content matches → evidence snapshot → officer notes and status control.
- Reuse the existing verdict-card, red-flag-highlighter, and risk-signal-map components from `frontend/src/analysisResults.jsx` and `features/result/RiskSignalMap.jsx` rather than rebuilding them.

### 6.4 Identifier and heat-list views
- Identifier page: every case containing it, a timeline, and its heat rank.
- Heat-list page: tabbed ranked tables with counts and trend arrows.

### 6.5 Server-side investigation report
- New: `app/services/report_builder.py` — generates a PDF/HTML report server-side (the current `frontend/src/lib/report.js` is client-only and redaction-first, which is the opposite of what an investigator needs).
- Report contents: case ID, submission time, artifact hash, full analysis with every triggered indicator, all extracted identifiers in a structured table, linked cases, evidence snapshot, and an audit trail of who viewed or modified the case.
- Provide **both** modes: redacted (citizen/public sharing — reuse `redaction.js` logic) and full (officer, authenticated). The existing masking work becomes a feature, not an obstacle.
- Add bulk export: all cases matching the current filter → CSV/JSON.

### 6.6 Citizen submission channel
- Add an "Also report this to police" opt-in on the existing `/result` page. Consent is explicit; an unchecked box keeps the current zero-storage behaviour.
- Submitted items enter the officer queue with `source=CITIZEN`, `status=NEW`.

**Exit criteria**
- An officer can log in, search cases, open one, pivot to an identifier, see linked cases, and download a full report.
- A citizen can opt in to forward a result, and it appears in the officer queue.
- Citizen mode with the opt-in unchecked still writes nothing to the database — verify with a test.

**Estimated effort:** 10–12 hours
**Risk:** Dashboard UI work expands without limit. Build the case list, case detail, and report download first; everything else is secondary.

---

## Phase 7 — Hardening & Demo Readiness ✅ COMPLETE (7.1–7.3, 7.6)

> **Delivered.** Suite: **246 passed, 6 skipped, 0 failed**. Browser: **25/25**.
>
> **Built:** `app/db/demo_seed.py` (14 cross-linked demo cases) · `DEMO.md` (five-minute runbook, failure table, anticipated judge questions) · extended `/health` reporting database and per-analyser availability · README rewritten for dual-mode, with a Known Limitations table.
>
> ### Four real bugs found during hardening — three only visible from rendered output
>
> **1. Foreign keys were never enforced (data corruption).** SQLite ignores foreign keys unless the `foreign_keys` pragma is set per connection, so every `ondelete="CASCADE"` in the models was inert. Deleting a case left its identifiers orphaned — polluting the heat-list permanently and colliding with reused row ids. Surfaced as an `IntegrityError` when re-running the seeder. Fixed with a connect-event pragma plus explicit child deletion, pinned by a test.
>
> **2. Courier scam classified as ROMANCE_SCAM.** The romance rule matched a bare `parcel … customs` with no relationship language. Visible only once seeded data was rendered in the dashboard.
>
> **3. Fake job classified as LOTTERY_PRIZE.** "Registration fee" carried the lottery category and outweighed the job rule. Same root cause as #2: a cross-cutting *tactic* claiming a fraud *family*. Fixed by splitting the fee rule and making `UNKNOWN` never outrank an identified category. Classification went from 10/12 to **12/12**, pinned by `test_scam_categories.py`.
>
> **4. Unrelated APKs reported as 66% repeat content.** Every APK's stored content is the same generated metadata layout, so hashing it matched a malicious loan app against a benign notes app. Similarity is now scoped to artifact types whose content is authored text.
>
> **Deferred by choice:** 7.4 browser extension and 7.5 Telegram bot. Both are PS01 *Good-to-Haves*, and the `/PARAKH/check-before-open` endpoint they would consume is already built, anonymous, and fast. Building either would have come at the cost of the hardening above.

**Goal:** Make the system survive a live demo, and add the differentiators only if the Must-Haves are genuinely complete.

### 7.1 Test coverage for new surfaces
- Extend the existing suite (`pytest.ini`, `testpaths = tests`):
  - `test_identifier_extractor.py` — positives and near-miss negatives for every pattern
  - `test_apk_analyzer.py` — against a benign sample APK fixture
  - `test_website_analyzer.py` — **including explicit SSRF-block assertions** for `127.0.0.1`, `169.254.169.254`, `10.x`, `192.168.x` at each redirect hop
  - `test_link_service.py` — linking and similarity correctness
  - `test_auth.py` — officer endpoints reject unauthenticated access
- Keep the existing rule: tests must pass with **no API key present**.

### 7.2 Resilience
- Every new analyser must degrade, never crash: RDAP down → `UNKNOWN` domain age; site unreachable → partial analysis with a stated limitation; Gemini down → deterministic rules still produce a verdict for all four artifact types.
- Add a `/api/v1/health` extension reporting DB connectivity and per-analyser availability.

### 7.3 Seed data and demo script
- Load the R4C sample dataset into the DB **before** the demo so the dashboard, heat-list, and linking views have realistic density. An empty dashboard demos badly.
- Plant deliberate cross-links in the seed data: the same phone number in an SMS, an APK, and a betting site — so the linking feature has something compelling to show.
- Write a 5-minute demo runbook: scam SMS → risk + identifiers → APK upload → same C2 domain appears → website → same UPI ID → dashboard shows all three linked → download report.

### 7.4 Good-to-have: browser extension
- Manifest V3 extension calling the Phase 5.5 `/check-before-open` endpoint.
- Intercepts navigation, shows an interstitial warning for HIGH-risk destinations.
- Only attempt this if Phases 1–6 are complete; it is explicitly a Good-to-Have.

### 7.5 Good-to-have: Telegram bot
- Telegram is lower-friction than WhatsApp (no Business API approval needed) and PS01 accepts either.
- Forward a message → bot replies with risk level and reasons, optionally filing a case.

### 7.6 Documentation
- Update `README.md`: new architecture, the dual-mode privacy model, API reference for all new endpoints, deployment notes for the persistent-host decision from Phase 1.1.
- Document limitations honestly: no dynamic analysis, obfuscated APKs yield less, JS-rendered sites may return thin content, no takedown capability. Judges respond well to stated limits; it signals the team understands the problem.

**Estimated effort:** 6–8 hours (plus 4–6 per good-to-have)

---

## Dependency Summary

Add to `requirements.txt`:

```
sqlalchemy>=2.0,<3.0
aiosqlite>=0.20,<1.0          # dev
asyncpg>=0.30,<1.0            # prod, if Postgres
passlib[bcrypt]>=1.7,<2.0
pyaxmlparser>=0.3,<1.0        # APK manifest
imagehash>=4.3,<5.0           # icon similarity (Pillow already present)
```

Already present and reused: `httpx` (RDAP, redirects, site fetch), `beautifulsoup4` (HTML parsing), `tldextract` (domain parsing), `Pillow` (icons, QR images), `pydantic` v2, `pytest`.

Optional / stretch: `androguard` (deep DEX), `pyzbar` (QR decode), `opencv-python-headless`.

---

## Phase Dependency Order

```
Phase 1 (Foundation + DB)
   │
   ├──> Phase 2 (Message/URL + IDENTIFIER EXTRACTOR) ──┐
   │         │                                          │
   │         ├──> Phase 3 (APK) ─────────────────────┤
   │         └──> Phase 4 (Website) ─────────────────┤
   │                                                   │
   │                                                   v
   └──────────────────────────> Phase 5 (Linking, Similarity, Heat-list)
                                            │
                                            v
                                Phase 6 (Dashboard + Reports)
                                            │
                                            v
                                Phase 7 (Hardening + Good-to-haves)
```

**Critical path note:** Phase 2.1 (identifier extractor) is the keystone. Phases 3, 4, and 5 all consume it. Build and test it before starting APK or website work — a weak extractor silently degrades every downstream feature.

Phases 3 and 4 are independent of each other and can be built in parallel by two people. PS01's Must-Have requires *at least one* of APK or website analysis — if time is short, finish one completely rather than leaving both half-done.

---

## 24-Hour Final Sprint Mapping

Assuming Phases 1–2 are complete before the final (strongly recommended — they are foundation work with no demo value on their own):

| Hours | Focus | Deliverable |
|---|---|---|
| 0–1 | Setup, seed R4C sample data, team split | Working baseline, populated DB |
| 1–7 | **Phase 3** (APK) in parallel with **Phase 4** (Website) | Both analysers returning risk + identifiers |
| 7–11 | **Phase 5** — linking, similarity, heat-list | Cross-source intelligence working |
| 11–18 | **Phase 6** — dashboard, case detail, identifier views | Officer console usable end to end |
| 18–21 | **Phase 6.5** — server-side report generation, bulk export | Downloadable investigation report |
| 21–23 | **Phase 7.1–7.3** — resilience passes, seed polish, demo runbook | Demo rehearsed twice |
| 23–24 | Buffer | Fix whatever broke during rehearsal |

Good-to-haves (7.4, 7.5) are only attempted if the team is ahead of this schedule.

---

## Must-Have Compliance Check

| PS01 Must-Have | Delivered by | Confidence |
|---|---|---|
| Analyse a message or URL and return a risk level with the reasons | Phases 1–2 (building on existing `scam_analyzer` + `url_intelligence`) | **High** — mostly exists today |
| Analyse at least one APK **or** one website and extract identifiers | Phase 3 **or** Phase 4 (both planned; one suffices) | **Medium** — entirely new, Phase 3 is the heaviest lift |
| A dashboard with case history, search and a downloadable report | Phases 1, 5, 6 | **Medium** — new, but conventional CRUD + search once the DB exists |

### Honest overall assessment

The existing codebase gives a genuine head start on the message, email, and URL analysis pipeline — including the explainability contract, the offline fallback, and the security middleware, all of which are better than what most teams will build from scratch in 24 hours.

It contributes **nothing** to APK analysis, website content analysis, or the investigation dashboard, which together represent the majority of PS01's distinctive value. Realistically about **35–40%** of the final deliverable is reusable code; the rest is new.

The reuse is real but it is concentrated in one of the three Must-Haves. Plan the schedule around the two that start from zero.

