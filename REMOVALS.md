# Removal Backlog — clean up at the END, not during development

**Rule: nothing here gets deleted until the PS01 build is feature-complete and demo-rehearsed.** Deleting early risks breaking a dependency we haven't discovered yet. Each entry records *what*, *why it became unnecessary*, and *what to check before deleting*.

Status: `CANDIDATE` (likely remove) · `DECIDE` (needs a call) · `KEEP` (evaluated, staying)

---

## A. Dead code / legacy

| # | Item | Why | Check before deleting | Status |
|---|---|---|---|---|
| A-1 | `/scamshield/analyze` route — `app/api/routes.py:297-310` | Deprecated compatibility alias, already `include_in_schema=False`. Nothing in `frontend/src/lib/api.js` calls it. | grep frontend + tests for `scamshield` | **CANDIDATE** |
| A-2 | `.packages/` directory (~15,000 files) | Vendored site-packages, already gitignored, not on `sys.path`. Pure disk noise; it dominates every glob/search in the repo. | Confirm nothing imports from it | **CANDIDATE** |
| A-3 | Stale `__pycache__` for cpython-311 / cpython-312 | venv is now Python 3.14. These are orphaned bytecode from earlier interpreters. | None — safe | **CANDIDATE** |
| A-4 | `frontend/stitch_PARAKH_india_cyber_safety_assistant/` (7 × `code.html`) | Design-tool mockup exports. Not imported by Vite, not referenced by any component. | Confirm not linked from docs | **CANDIDATE** |
| A-5 | `ReportPackDraft` + `EvidenceItem` in `app/schemas.py:523-543` | Defined server-side but never used by any route — evidence is client-only today. Phase 6 replaces them with real DB-backed report models. | Supersede in Phase 6, then delete | **CANDIDATE** |

---

## B. Citizen features outside PS01 scope

PS01 is investigation-focused. ADR-001 keeps Citizen Mode, so these are **not automatically removable** — the question is whether each still earns its place in the demo. Decide after Phase 6, when we know how much screen time the dashboard needs.

| # | Item | PS01 relevance | Status |
|---|---|---|---|
| B-1 | Rescue Mode — `services/rescue_planner.py`, `data/recovery_playbooks.py`, `features/rescue/`, `/rescue` route | Post-exposure victim guidance. Not requested by PS01, but demos well as "citizen value" and costs nothing to keep running. | **DECIDE** |
| B-2 | Evidence Locker — `features/evidence/EvidenceLocker.jsx`, `lib/vault.js` (AES-GCM IndexedDB) | Directly superseded by server-side cases. Keeping both creates two competing evidence stores and confuses the story. | **CANDIDATE** after Phase 6 |
| B-3 | Safe Next Step — `services/decision_checker.py`, `data/decision_playbooks.py` | Citizen pre-action advice. Partially overlaps PS01's "warn users before they open a risky link", which Phase 5.5 implements server-side instead. | **DECIDE** |
| B-4 | Organisation Verifier — `services/organisation_verifier.py`, `data/official_directory.py` | Citizen verification helper. No PS01 equivalent. | **DECIDE** |
| B-5 | Trusted Channels — `services/trusted_channel_service.py`, `data/trusted_channels.py` | Static reporting directory. No PS01 equivalent. | **DECIDE** |
| B-6 | Simple Explainer — `services/simple_explainer.py`, `data/simple_explanations.py` | Plain-language Hindi/Hinglish output. PS01 wants explainability, but for *officers* — different register. | **DECIDE** |
| B-7 | QR Analyzer — `services/qr_analyzer.py`, `data/qr_playbooks.py`, `features/qr/` | **Likely KEEP** — Phase 4.4 decodes UPI QRs found on fraud websites and can reuse this payload logic. | **KEEP** (re-evaluate) |
| B-8 | Voice guidance — `lib/voiceGuidance.js`, `features/accessibility/VoiceGuidance.jsx` | Browser TTS for citizens. No PS01 equivalent. | **DECIDE** |
| B-9 | Learn page — `pages/LearnPage.jsx`, `features/learn/*` | Scam-literacy education. No PS01 equivalent. | **DECIDE** |
| B-10 | Media analysis — `services/media_analyzer.py`, `media_validation.py` | **KEEP** — PS01 sample data explicitly includes *"screenshots or saved pages of fraudulent investment, betting and Ponzi websites"*. OCR on those is directly useful. | **KEEP** |

---

## C. Superseded by the pivot

| # | Item | Superseded by | Status |
|---|---|---|---|
| C-1 | Client-side-only PDF generation as the *primary* report path — `frontend/src/lib/report.js` | Phase 6.5 server-side `report_builder.py`. **Keep `redaction.js`** — its masking logic is reused for the redacted report mode. | **DECIDE** (keep redaction) |
| C-2 | `vercel.json` single-deployment config | ADR-003 moves the investigation backend to a persistent host. Rewrite rather than delete if the citizen SPA stays on Vercel. | **DECIDE** |
| C-3 | README sections describing "no server-side storage" as absolute | ADR-001 dual-mode. Must be rewritten in Phase 7.6 or the docs actively contradict the product. | **MUST UPDATE** |

---

## D. Added during Phases 1–2 — remove only if unused at the end

| # | Item | Remove if |
|---|---|---|
| D-1 | `app/db/seed.py` blacklist seeder | Never — needed for demo. Keep out of the production startup path. |
| D-2 | Verbose SQL echo logging | Always off before demo (`DB_ECHO=false` — already the default). |
| D-3 | Synthetic entries in `app/data/blacklists.py` | Replace with R4C sample-dataset entries once available. The placeholder values (`sbi-verify-kyc.in`, `winner@ybl`, `+919876543210`, `com.quickloan.instant`) must not ship as if they were real intelligence. |
| D-4 | `PARAKH_cases.db` in the repo root | Never commit it. Add to `.gitignore` before the first commit after Phase 1. |
| D-5 | Default officer password `ChangeThisBeforeDemo123` in `.env` | Must be changed before any public demo. `.env` is gitignored, but the value is weak and currently grants full case access. |
| D-6 | ~~`test_apk_submission_is_rejected_until_phase_three`~~ | **Resolved in Phase 3.** Renamed to `test_apk_cannot_be_submitted_as_text` — the 422 is still correct behaviour (APKs are binaries and must use `/apk/analyze`), only the name was stale. |
| D-7 | `tests/apk_fixtures.py` | Never — it is the only way to test APK analysis without shipping a binary sample. Keep out of any production build. |
| D-8 | Icon dHash on flat images | Known limitation, not a removal: a solid-colour icon hashes to all zeros and cannot be compared. Only matters if real fixtures turn out to be flat. |
| D-9 | Hardcoded fetch limits in `website_analyzer.py` | Keep as module constants. They are safety boundaries (2 MB cap, 10s timeout, 3 redirects), not tuning knobs, and should not be weakened from a config file. |
| D-10 | `tldextract` `registered_domain` deprecation warning | Noise in test output from `url_intelligence.py:262`. Harmless — the code already prefers `top_domain_under_public_suffix` — but the fallback `getattr` still triggers it. Tidy before the demo. |
| D-11 | Synthetic `richplan-invest.xyz` / `fraudster@ybl` demo values | Same as D-3: replace with R4C dataset values. These now also appear in `tests/` and the demo scripts. |
| D-12 | ~~`tldextract` deprecation warning~~ | **Resolved in Phase 7** — the deprecated fallback is now only reached when the new property is genuinely absent. |
| D-13 | `app/db/demo_seed.py` | Keep for demos; exclude from any production startup path. Its `--reset` flag deletes all cases, so never expose it as an endpoint. |
| D-14 | `DEMO.md` | Keep through judging. Delete or move to `docs/` afterwards. |
| D-15 | `samples/` (APKs from `demo_seed --export-apks`) | Generated on demand and gitignored. Never commit; replace with R4C sample APKs when available. |
| D-16 | `--export-apks` imports `tests/apk_fixtures.py` | Same rule as D-7: demo tooling only, keep out of any production build. |

---

## E. Resolved during build

| # | Item | Outcome |
|---|---|---|
| E-1 | ADR-001 enforcement | Pinned by `test_citizen_mode_analysis_persists_nothing` and three citizen-reporting consent tests. Do not delete these; they are the privacy guarantee. |
| E-2 | SQLite foreign-key enforcement | Fixed in `app/db/session.py` via a connect-event pragma. Removing it silently reintroduces orphaned identifier rows. |
| E-3 | Similarity scoping | `_SIMILARITY_ARTIFACTS` in `case_service.py` deliberately excludes APK. Adding APK back reintroduces false repeat-content matches between unrelated apps. |
| E-4 | Campaign link rules | `links_cases()` and `GENERIC_HOSTS` in `link_service.py`. Removing them lets `t.me`, `bit.ly`, full URLs or an IFSC branch code merge unrelated campaigns into one blob. |
| E-5 | High-risk-only history for App check | `reported_matches()` counts only HIGH-risk cases. Widening it makes a benign app an officer once analysed show as "Already seen in police cases". |
| E-6 | Account label beats phone shape | `_ACCOUNT_LABEL` in `identifier_extractor.py`. Without it, `A/c 918273645501` is extracted as phone `+918273645501`. |
| E-7 | Rename encoding damage | The PARAKH rename (PowerShell 5.1) wrote 36 files with a BOM and mojibake, including every Hindi explanation in `scam_rules.py`, and collapsed the Redis rate-limit key to a constant. All repaired; never bulk-edit with `Get-Content`/`Set-Content` without `-Encoding utf8`. |

---

## Pre-deletion checklist

Before removing anything above:

1. `pytest -q` is green **before** the deletion
2. `grep -rn "<symbol>" app/ tests/ frontend/src/` returns no live references
3. `cd frontend; npm run build` still succeeds
4. Delete in one commit per item, so a bad call is a single `git revert`

