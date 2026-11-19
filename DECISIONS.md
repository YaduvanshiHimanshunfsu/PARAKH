# Architecture Decisions â€” PS01 Conversion

Decision record for converting PARAKH to Rajasthan Police PS01. Each entry states the context, the decision taken, its consequences, and what was rejected.

Status legend: **Accepted** Â· **Proposed** Â· **Superseded**

---

## Verified Baseline (Phase 0.1)

Measured on 2026-11-18, not assumed from reading code.

| Check | Result |
|---|---|
| Python (venv + system) | 3.14.0 â€” note: stale `__pycache__` from 3.11/3.12 present |
| Backend dependencies | All 15 present (`fastapi`, `google.genai`, `pydantic`, `tldextract`, `PIL`, `bs4`, `dns`, `dkim`, â€¦) |
| Test suite | **31 passed, 6 skipped, 0 failed** in ~9.8s |
| Skipped tests | 6, all Windows-only: *"Local Windows asyncio runtime cannot create its self-pipe"* â€” covers `test_security_headers.py`, `test_scam_analyzer_provider.py`, `test_media_analyzer_provider.py` |
| App boot | OK â€” `/api/v1/health` â†’ 200 |
| Frontend | `node_modules` present, `frontend/dist` present (committed build) |
| Git | Repo at `main`, 3 commits, clean tree |
| `.env` | Was **missing** â€” created in Phase 0.3 |

### Live analysis smoke test

Input: `"Dear customer your SBI KYC will be blocked in 24 hours. Verify at sbi-verify-kyc.in/urgent or call 9876543210"`

```
verdict      SCAM   confidence 96   category KYC_SCAM   source RULE_FALLBACK
red_flags    ['KYC', 'blocked', 'in 24 hours', 'sbi-verify-kyc.in/urgent']
url_analyses [('sbi-verify-kyc.in/urgent', 'MEDIUM', 33)]
latency      1113 ms
```

### Four defects found during baseline verification

**B-1 â€” Invalid Gemini key in the OS environment (demo-blocking).**
`GEMINI_API_KEY` is set as a Windows user environment variable (53 chars) and returns **HTTP 401** on every call. The app reports `provider_configured: true`, then burns three sequential failed model attempts before falling back â€” **1113 ms of pure dead latency per analysis**. `pydantic-settings` ranks OS environment variables above `.env`, so this cannot be fixed by editing `.env`; it must be cleared or replaced at the OS level.
*Impact:* every demo request is ~1.1s slower than necessary, and the live-AI path is entirely non-functional.

**B-2 â€” `CREDENTIAL_OR_KYC_LURE` ignores the hostname.**
`url_intelligence.py:336` matches `SENSITIVE_PATH_TERMS` against `path + query` only. The domain `sbi-verify-kyc.in` contains both *verify* and *kyc* in the **host** and scores nothing for it. Only `BRAND_LIKE_DOMAIN` (+25) fired. A textbook SBI-lookalike phishing domain is rated **MEDIUM/33** when it should be HIGH.
*Fix:* Phase 2 â€” extend the match to the hostname with its own signal code.

**B-3 â€” No identifier extraction, confirmed empirically.**
The phone number `9876543210` in the test message was not extracted anywhere in the response. Confirms the Phase 2.1 gap is real, not theoretical.

**B-4 â€” Six tests never execute on Windows.**
The security-headers and both provider contract tests are skipped locally. The team is developing without local verification of the security middleware. Needs a Linux CI runner or WSL before relying on them.

---

## ADR-001 â€” Dual-mode privacy: Citizen (ephemeral) + Investigation (persistent)

**Status:** Accepted

### Context
PARAKH's defining design choice is that it stores nothing server-side. The README states it plainly: *"The backend intentionally has no endpoint for evidence contents or report packs."* Evidence lives in browser IndexedDB under a non-extractable AES-GCM key.

PS01 requires the opposite: *"maintain searchable records and evidence reports for police investigation."*

These cannot both be the default.

### Decision
Run two modes against one analysis engine.

- **Citizen Mode** â€” existing routes (`/PARAKH/analyze`, `/url/analyze`, `/email/analyze`, â€¦) keep their current contract and write **nothing** to the database. Current behaviour is preserved byte-for-byte.
- **Investigation Mode** â€” a new `/api/v1/investigate/*` route group persists a full case: artifact, findings, identifiers, evidence snapshot.
- A citizen moves between them only by **explicit opt-in** ("Also report this to police"), unchecked by default.

### Consequences
- Both the privacy story and the police requirement survive; neither is a compromise of the other.
- The analysis services must be refactored to return a reusable `AnalysisBundle` rather than writing responses directly (Phase 1.3).
- A test must assert that Citizen Mode with the opt-in unchecked produces zero database rows. Without it, this decision silently rots.

### Rejected
- *Persist everything.* Simpler, but discards the project's strongest existing differentiator and is hard to defend on consent grounds.
- *Keep client-only storage.* Cannot deliver a searchable dashboard, cross-case linking, or a heat-list â€” three of PS01's named features.

---

## ADR-002 â€” Guarded content fetching for website analysis

**Status:** Accepted

### Context
`url_intelligence.py` documents its own restraint at line 83: it *"never follows redirects, downloads page content, runs JavaScript, or submits unknown links."* `_normalise()` additionally **rejects** direct-IP hosts, non-standard ports, and embedded credentials.

PS01 requires examining *"promotional content for guaranteed returns, referral-chain (MLM) language and betting indicators"* and extracting UPI IDs, bank details and crypto wallets from pages. That is impossible without fetching.

### Decision
Add a **separate** `app/services/website_analyzer.py` rather than loosening the existing service. Constraints, all mandatory:

- 10s total timeout, 2 MB streamed response cap (abort on exceed)
- Maximum 3 redirects, resolved hop-by-hop with `follow_redirects=False`
- **SSRF guard re-applied at every hop**, reusing the existing `_public_addresses()` helper
- No JavaScript execution; HTML/text content types only
- Fetch is never implicit in Citizen Mode â€” it requires a deliberate user or officer action
- Fetch time and final resolved URL are recorded as evidence

Separately, in **Investigation Mode only**, the three `_normalise()` refusals become HIGH-severity findings (`DIRECT_IP_HOST`, `NON_STANDARD_PORT`, `EMBEDDED_CREDENTIALS`) instead of errors. For a citizen, refusing is correct. For an investigator, those *are* the evidence.

### Consequences
- The citizen-facing no-fetch guarantee remains literally true.
- SSRF becomes the highest-severity security risk in the project. Phase 7.1 requires explicit tests against `127.0.0.1`, `169.254.169.254`, `10.x`, and `192.168.x` at **each** redirect hop, not just the first.
- JS-rendered fraud sites will return thin content. This is stated as a limitation in output rather than silently producing a weak verdict.

### Rejected
- *Modify `url_intelligence.py` in place.* Would break the documented citizen guarantee and the existing tests that depend on it.
- *Headless browser (Playwright) rendering.* Correct for JS-heavy sites, but heavy to add server-side and a poor use of a 24-hour budget. Kept as a stretch goal.

---

## ADR-003 â€” SQLite + async SQLAlchemy, local-first deployment

**Status:** Accepted

### Context
There is no database today. Three options were weighed: SQLite, hosted Postgres (Neon/Supabase), and Turso/libSQL.

The deployment target matters as much as the engine. The project currently targets Vercel serverless, where the filesystem is ephemeral â€” a SQLite file written during one request is gone by the next. APK uploads (5â€“60 MB) also exceed Vercel's payload ceiling, and `max_request_bytes` is capped at 4 MB in `config.py:58` precisely because of it.

### Decision
- **SQLite via async SQLAlchemy 2.0 + `aiosqlite`** for development and the hackathon demo.
- All models written against the SQLAlchemy ORM so moving to Postgres is a connection-string change plus `asyncpg`. No SQLite-specific SQL.
- **The investigation backend runs on a persistent host, not Vercel serverless** â€” a laptop for the demo, or a VPS/Render/Railway instance.
- The citizen SPA may continue to deploy on Vercel independently if desired.

### Consequences
- Zero infrastructure setup and no network dependency during the demo â€” the single biggest reliability win for a live 24-hour judging environment.
- The current `vercel.json` single-deployment model no longer covers the whole product. README deployment notes need rewriting (Phase 7.6).
- Concurrent write throughput is limited, which is irrelevant at demo scale.

### Rejected
- *Hosted Postgres from the start.* More production-realistic, but adds a network dependency to a live demo and costs setup time that Phase 3 needs more.
- *Staying fully on Vercel.* Incompatible with both durable storage and APK upload sizes. Not viable.

---

## ADR-004 â€” Per-route upload limits

**Status:** Accepted

### Context
`RequestSizeLimitMiddleware` enforces a single global `max_request_bytes` (3.25 MB) across every POST. `config.py` hard-caps the setting at 4 MB (`le=4_000_000`). Real APKs routinely exceed both.

### Decision
Keep the global middleware limit as-is for all existing routes. The APK route performs its **own** size check (~60 MB) and is exempted from the global middleware by path. Raising the global ceiling is explicitly avoided â€” it would widen the denial-of-service surface on every text endpoint to protect one upload route.

### Consequences
- `config.py`'s `le=4_000_000` constraint stays valid; a separate `max_apk_upload_bytes` setting is added.
- The middleware needs a path-exemption list, which is a small and reviewable change.

### Rejected
- *Raise the global limit to 60 MB.* Exposes every JSON endpoint to 60 MB request bodies.

---

## ADR-005 â€” Deterministic-first for APK and website analysis

**Status:** Accepted

### Context
The baseline smoke test demonstrated this risk concretely: with an invalid API key, every Gemini call failed and the **rule-based fallback still returned `SCAM / 96 / KYC_SCAM` with four correct red flags**. The fallback is the reason the product still worked.

Message analysis has that safety net. If APK and website analysis were built AI-first, they would have none.

### Decision
APK analysis (Phase 3) and website analysis (Phase 4) are **fully deterministic** â€” permission rules, certificate inspection, regex identifier extraction, and keyword scoring. Gemini may later *enrich* their output (e.g. summarising a site's pitch), never *produce* the verdict.

### Consequences
- Both new analysers work with no API key, no quota, and no network dependency beyond fetching the target itself.
- Rules live in version-controlled data files (`app/data/apk_permission_rules.py`, `app/data/website_rules.py`) matching the existing `ScamSignalRule` pattern, so every finding is explainable and auditable â€” which is what PS01 means by explainable risk.
- Detection quality depends on rule-pack quality. Budget real time for writing rules, not just plumbing.

### Rejected
- *Send the manifest or page text to Gemini for a verdict.* Faster to build, but the demo then dies with the API key â€” exactly the failure already observed in baseline testing.

---

## Open Items

| # | Item | Needed by | Owner |
|---|---|---|---|
| O-1 | Clear or replace the invalid OS-level `GEMINI_API_KEY` (B-1) | Before any live-AI demo | â€” |
| O-2 | Obtain the R4C sample dataset; confirm APK samples are included | Phase 3 start | â€” |
| O-3 | Decide officer-auth mechanism: shared bearer token vs. seeded user accounts | Phase 1.4 | â€” |
| O-4 | Set up Linux CI or WSL so the 6 skipped tests actually run (B-4) | Phase 7.1 | â€” |
| O-5 | Confirm whether the final demo runs on a team laptop or hosted infrastructure | Phase 1.1 | â€” |

