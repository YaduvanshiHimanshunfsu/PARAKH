# Removal Backlog â€” clean up at the END, not during development

**Rule: nothing here gets deleted until the PS01 build is feature-complete and demo-rehearsed.** Deleting early risks breaking a dependency we haven't discovered yet. Each entry records *what*, *why it became unnecessary*, and *what to check before deleting*.

Status: `CANDIDATE` (likely remove) Â· `DECIDE` (needs a call) Â· `KEEP` (evaluated, staying)

---

## A. Dead code / legacy

| # | Item | Why | Check before deleting | Status |
|---|---|---|---|---|
| A-1 | `/scamshield/analyze` route â€” `app/api/routes.py:297-310` | Deprecated compatibility alias, already `include_in_schema=False`. Nothing in `frontend/src/lib/api.js` calls it. | grep frontend + tests for `scamshield` | **CANDIDATE** |
| A-2 | `.packages/` directory (~15,000 files) | Vendored site-packages, already gitignored, not on `sys.path`. Pure disk noise; it dominates every glob/search in the repo. | Confirm nothing imports from it | **CANDIDATE** |
| A-3 | Stale `__pycache__` for cpython-311 / cpython-312 | venv is now Python 3.14. These are orphaned bytecode from earlier interpreters. | None â€” safe | **CANDIDATE** |
| A-4 | `frontend/stitch_PARAKH_india_cyber_safety_assistant/` (7 Ã— `code.html`) | Design-tool mockup exports. Not imported by Vite, not referenced by any component. | Confirm not linked from docs | **CANDIDATE** |
| A-5 | `ReportPackDraft` + `EvidenceItem` in `app/schemas.py:523-543` | Defined server-side but never used by any route â€” evidence is client-only today. Phase 6 replaces them with real DB-backed report models. | Supersede in Phase 6, then delete | **CANDIDATE** |

---

## B. Citizen features outside PS01 scope

PS01 is investigation-focused. ADR-001 keeps Citizen Mode, so these are **not automatically removable** â€” the question is whether each still earns its place in the demo. Decide after Phase 6, when we know how much screen time the dashboard needs.

| # | Item | PS01 relevance | Status |
|---|---|---|---|
| B-1 | Rescue Mode â€” `services/rescue_planner.py`, `data/recovery_playbooks.py`, `features/rescue/`, `/rescue` route | Post-exposure victim guidance. Not requested by PS01, but demos well as "citizen value" and costs nothing to keep running. | **DECIDE** |
| B-2 | Evidence Locker â€” `features/evidence/EvidenceLocker.jsx`, `lib/vault.js` (AES-GCM IndexedDB) | Directly superseded by server-side cases. Keeping both creates two competing evidence stores and confuses the story. | **CANDIDATE** after Phase 6 |
| B-3 | Safe Next Step â€” `services/decision_checker.py`, `data/decision_playbooks.py` | Citizen pre-action advice. Partially overlaps PS01's "warn users before they open a risky link", which Phase 5.5 implements server-side instead. | **DECIDE** |
| B-4 | Organisation Verifier â€” `services/organisation_verifier.py`, `data/official_directory.py` | Citizen verification helper. No PS01 equivalent. | **DECIDE** |
| B-5 | Trusted Channels â€” `services/trusted_channel_service.py`, `data/trusted_channels.py` | Static reporting directory. No PS01 equivalent. | **DECIDE** |
| B-6 | Simple Explainer â€” `services/simple_explainer.py`, `data/simple_explanations.py` | Plain-language Hindi/Hinglish output. PS01 wants explainability, but for *officers* â€” different register. | **DECIDE** |
| B-7 | QR Analyzer â€” `services/qr_analyzer.py`, `data/qr_playbooks.py`, `features/qr/` | **Likely KEEP** â€” Phase 4.4 decodes UPI QRs found on fraud websites and can reuse this payload logic. | **KEEP** (re-evaluate) |
| B-8 | Voice guidance â€” `lib/voiceGuidance.js`, `features/accessibility/VoiceGuidance.jsx` | Browser TTS for citizens. No PS01 equivalent. | **DECIDE** |
| B-9 | Learn page â€” `pages/LearnPage.jsx`, `features/learn/*` | Scam-literacy education. No PS01 equivalent. | **DECIDE** |
| B-10 | Media analysis â€” `services/media_analyzer.py`, `media_validation.py` | **KEEP** â€” PS01 sample data explicitly includes *"screenshots or saved pages of fraudulent investment, betting and Ponzi websites"*. OCR on those is directly useful. | **KEEP** |

---

## C. Superseded by the pivot

| # | Item | Superseded by | Status |
|---|---|---|---|
| C-1 | Client-side-only PDF generation as the *primary* report path â€” `frontend/src/lib/report.js` | Phase 6.5 server-side `report_builder.py`. **Keep `redaction.js`** â€” its masking logic is reused for the redacted report mode. | **DECIDE** (keep redaction) |
| C-2 | `vercel.json` single-deployment config | ADR-003 moves the investigation backend to a persistent host. Rewrite rather than delete if the citizen SPA stays on Vercel. | **DECIDE** |
| C-3 | README sections describing "no server-side storage" as absolute | ADR-001 dual-mode. Must be rewritten in Phase 7.6 or the docs actively contradict the product. | **MUST UPDATE** |

---

## D. Added during Phases 1â€“2 â€” remove only if unused at the end

| # | Item | Remove if |
|---|---|---|
| D-1 | `app/db/seed.py` blacklist seeder | Never â€” needed for demo. Keep out of the production startup path. |
| D-2 | Verbose SQL echo logging | Always off before demo (`DB_ECHO=false` â€” already the default). |
| D-3 | Synthetic entries in `app/data/blacklists.py` | Replace with R4C sample-dataset entries once available. The placeholder values (`sbi-verify-kyc.in`, `winner@ybl`, `+919876543210`, `com.quickloan.instant`) must not ship as if they were real intelligence. |
| D-4 | `PARAKH_cases.db` in the repo root | Never commit it. Add to `.gitignore` before the first commit after Phase 1. |
| D-5 | Default officer password `ChangeThisBeforeDemo123` in `.env` | Must be changed before any public demo. `.env` is gitignored, but the value is weak and currently grants full case access. |
| D-6 | ~~`test_apk_submission_is_rejected_until_phase_three`~~ | **Resolved in Phase 3.** Renamed to `test_apk_cannot_be_submitted_as_text` â€” the 422 is still correct behaviour (APKs are binaries and must use `/apk/analyze`), only the name was stale. |
| D-7 | `tests/apk_fixtures.py` | Never â€” it is the only way to test APK analysis without shipping a binary sample. Keep out of any production build. |
| D-8 | Icon dHash on flat images | Known limitation, not a removal: a solid-colour icon hashes to all zeros and cannot be compared. Only matters if real fixtures turn out to be flat. |
| D-9 | Hardcoded fetch limits in `website_analyzer.py` | Keep as module constants. They are safety boundaries (2 MB cap, 10s timeout, 3 redirects), not tuning knobs, and should not be weakened from a config file. |
| D-10 | `tldextract` `registered_domain` deprecation warning | Noise in test output from `url_intelligence.py:262`. Harmless â€” the code already prefers `top_domain_under_public_suffix` â€” but the fallback `getattr` still triggers it. Tidy before the demo. |
| D-11 | Synthetic `richplan-invest.xyz` / `fraudster@ybl` demo values | Same as D-3: replace with R4C dataset values. These now also appear in `tests/` and the demo scripts. |
| D-12 | ~~`tldextract` deprecation warning~~ | **Resolved in Phase 7** â€” the deprecated fallback is now only reached when the new property is genuinely absent. |
| D-13 | `app/db/demo_seed.py` | Keep for demos; exclude from any production startup path. Its `--reset` flag deletes all cases, so never expose it as an endpoint. |
| D-14 | `DEMO.md` | Keep through judging. Delete or move to `docs/` afterwards. |

---

## E. Resolved during build

| # | Item | Outcome |
|---|---|---|
| E-1 | ADR-001 enforcement | Pinned by `test_citizen_mode_analysis_persists_nothing` and three citizen-reporting consent tests. Do not delete these; they are the privacy guarantee. |
| E-2 | SQLite foreign-key enforcement | Fixed in `app/db/session.py` via a connect-event pragma. Removing it silently reintroduces orphaned identifier rows. |
| E-3 | Similarity scoping | `_SIMILARITY_ARTIFACTS` in `case_service.py` deliberately excludes APK. Adding APK back reintroduces false repeat-content matches between unrelated apps. |

---

## Pre-deletion checklist

Before removing anything above:

1. `pytest -q` is green **before** the deletion
2. `grep -rn "<symbol>" app/ tests/ frontend/src/` returns no live references
3. `cd frontend; npm run build` still succeeds
4. Delete in one commit per item, so a bad call is a single `git revert`

