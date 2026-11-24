# PARAKH — Plan Version Alpha

**Scope:** upgrade PARAKH from a strong hackathon prototype into a live-demo-proof, police-workflow-aware platform.
**Audience:** the PARAKH build team.
**Status legend:** `[ ]` not started · `[~]` in progress · `[x]` done
**Priority legend:** **P0** = must have before the jury · **P1** = strongly recommended · **P2** = stretch / scale proof

This plan sits on top of the existing documents. Read these first: [README.md](README.md), [DECISIONS.md](DECISIONS.md) (ADR-001…005), [PHASES.md](PHASES.md) (Phases 0–7, already delivered), [DEMO.md](DEMO.md), [REMOVALS.md](REMOVALS.md).

> **Revision 2 (24 Nov 2026): new frontend.** The previous React frontend (`frontend/src`, `dist`, e2e tests) was removed on purpose. The new UI is the Google Stitch export in [`frontend/stitch_parakh_design_system/stitch_parakh_design_system/`](frontend/stitch_parakh_design_system/stitch_parakh_design_system/): 31 screens plus the *Civic Vigilance Light* design system. **Phase H has been rewritten** to turn these static designs into the working React app, wired to the existing backend. Until Phase H.0–H.2 land, PARAKH has **no usable UI**, so Phase H is now **P0** and runs in parallel with Phase B. The wireframe sheet ([wireframe.jpg](wireframe.jpg)) remains the reference for screens Stitch has not produced yet.

---

## Table of contents

- [0. Ground rules for this plan](#0-ground-rules-for-this-plan)
- [1. Where we are today (verified baseline)](#1-where-we-are-today-verified-baseline)
- [2. Target scores](#2-target-scores)
- [3. Phase map](#3-phase-map)
- [Phase A — Measure first: golden dataset, evaluation harness, demo smoke suite (P0)](#phase-a--measure-first-golden-dataset-evaluation-harness-demo-smoke-suite-p0)
- [Phase B — Detection accuracy 5 → 8 (P0, the most important phase)](#phase-b--detection-accuracy-5--8-p0-the-most-important-phase)
- [Phase C — Officer hierarchy, jurisdiction and security (P0)](#phase-c--officer-hierarchy-jurisdiction-and-security-p0)
- [Phase D — Action layer: action pack, approval chain, dispatch, MIS (P1)](#phase-d--action-layer-action-pack-approval-chain-dispatch-mis-p1)
- [Phase E — Evidence integrity and court readiness (P1)](#phase-e--evidence-integrity-and-court-readiness-p1)
- [Phase F — Scalability 4 → 7.5 (P2)](#phase-f--scalability-4--75-p2)
- [Phase G — Intelligence extensions: money trail, jurisdiction intelligence (P2)](#phase-g--intelligence-extensions-money-trail-jurisdiction-intelligence-p2)
- [Phase H — New frontend: implement the Stitch design system and wire it to the backend (P0, runs in parallel)](#phase-h--new-frontend-implement-the-stitch-design-system-and-wire-it-to-the-backend-p0-runs-in-parallel)
- [Phase I — Demo readiness, deck and jury (P0, last)](#phase-i--demo-readiness-deck-and-jury-p0-last)
- [Appendix 1 — Study list and references](#appendix-1--study-list-and-references)
- [Appendix 2 — New files and folders](#appendix-2--new-files-and-folders)
- [Appendix 3 — New dependencies](#appendix-3--new-dependencies)

---

## 0. Ground rules for this plan

### 0.1 "Real logic, demo data": what may be hardcoded and what may not

This is a hackathon build. It does not need production infrastructure. It must still be honest: anything the jury sees being computed is actually computed.

| Allowed (hardcoding / seeding is fine) | Not allowed (counts as fakeness) |
|---|---|
| Demo units: one range, one district, 2–3 police stations | Pre-recorded or canned analysis results shown as live |
| Demo officer accounts (SP, DySP, SHO, IO, Operator) with seeded passwords | A verdict that does not come from the running rules or model |
| A static addressee directory (bank/PSP/telecom/registrar → "Nodal Officer, <org>"), clearly marked *sample* | Real officers' names, emails or phone numbers that we were not given |
| Legal templates marked **DRAFT — for officer review** | Claiming templates are legally vetted when they are not |
| Synthetic demo cases (`richplan@ybl`, `+91 98123 45670`, …) labelled as demo data | Statistics on slides that we did not measure or cannot source |
| Optional services switched off (Gemini, VirusTotal, timestamp authority) | Saying "AI-powered" for a result that came from rules (show the actual source tag) |
| Reference icon set built from apps we downloaded ourselves | Using official emblems or logos without authorisation |

### 0.2 Live-demo reliability rule

The artifact analysers must work **live, offline, every time**:

- message (English / Hindi / Hinglish)
- URL
- email (.eml)
- QR
- APK
- website

So:

1. **Offline-first.** Every analyser must return a correct verdict with **no API key and no internet**. RDAP, TLS probes and website fetching degrade to "not checked"; they never crash or block.
2. **Hard timeouts everywhere.** No request may hang the UI for more than 10 s.
3. **Golden demo inputs are regression-tested.** `scripts/demo_check.py` (Phase A) must pass before every rehearsal and on demo morning.
4. **Never trust a feature we have not run.** A feature counts as done only when its tests pass *and* it has been exercised in the browser.

### 0.3 Engineering rules (carry over from the existing project)

- Deterministic rules decide the verdict. AI may *enrich* or *raise* a verdict, never silently *lower* a strong rule verdict (see B.9).
- Every finding is explainable: a rule ID, a plain-language reason and the matched evidence.
- Citizen mode still stores nothing unless the citizen consents (ADR-001). The existing tests that enforce this must keep passing.
- No bulk edits with PowerShell `Set-Content` without `-Encoding utf8` (see REMOVALS.md E-7; it corrupted Hindi text before).

---

## 1. Where we are today (verified baseline)

**Test suite:** 274 passed, 6 skipped (the skips are Windows-only asyncio tests).

### 1.1 Officer features that already exist

| # | Feature | Where |
|---|---|---|
| 1 | Secure sign-in: scrypt password hashes, SHA-256-hashed bearer tokens, 12 h expiry, `sessionStorage`, logout revokes the token, generic error on failure | `app/core/auth.py`, `app/api/investigate.py` |
| 2 | Every analysis becomes a case (Message, URL, Email, APK up to 60 MB, Website) | `app/services/case_service.py` |
| 3 | Deeper officer-only analysis: RDAP domain age, SSRF-guarded redirect chains, blacklist matching, guarded website fetch, full APK breakdown | `url_enrichment.py`, `website_analyzer.py`, `apk_analyzer.py` |
| 4 | Identifier extraction (14 types), normalised | `identifier_extractor.py` |
| 5 | Search and identifier pivot | `case_service.search_cases`, `link_service.cases_for_identifier` |
| 6 | Weighted linked cases | `link_service.linked_cases` |
| 7 | Repeat-content detection (template hash + SimHash) | `utils/fingerprint.py`, `link_service.similar_cases` |
| 8 | Campaign map with variant timeline and word diffs | `campaign_service.py` (backend). The UI was removed with the old frontend and is rebuilt in Phase H.4 |
| 9 | Heat-list with 7-day trend | `link_service.heat_list` |
| 10 | Case status, notes, full/redacted HTML report, JSON, CSV | `report_builder.py` |
| 11 | Citizen "Report to police" queue (consent-gated) | `routes.py /parakh/report-to-police` |

### 1.2 Defects confirmed by running the engine (these drive Phase B)

| ID | Defect | Evidence |
|---|---|---|
| D1 | Official sites flagged `BRAND_LIKE_DOMAIN`: `police.rajasthan.gov.in`, `cybercrime.gov.in`, `firstpost.com`, `sbicard.com`, `pineapple.com` all scored MEDIUM/25 | Substring check at `app/services/url_intelligence.py:359` |
| D2 | Offline engine scores Devanagari scams SAFE | Hindi KYC and "account closed, click link" → SAFE |
| D3 | "Digital arrest" and task scams score SAFE offline | Probe messages → SAFE |
| D4 | Extractor misses USDT-TRC20, `@telegram` handles, foreign numbers, landlines, new TLDs (`.cyou`) | Probe text |
| D5 | Telegram bot token read as phone `+917012345678` | Probe text |
| D6 | Official/brand domains (`sbi.co.in`, `incometax.gov.in`) link unrelated cases | `link_service.links_cases` returns `True` |
| D7 | Citizen screenshot/voice extraction returned 404 (the old client called `/PARAKH/media/extract`; the route is lowercase). **The new frontend must use lowercase `/api/v1/parakh/...` paths everywhere** (H.0 API client) | old `frontend/src/lib/api.js:37` (removed) |
| D8 | APK accessibility detection only reads `<uses-permission>`; real malware declares it on `<service android:permission>` | `app/data/apk_permission_rules.py:66`, fixture in `tests/test_apk_analyzer.py` |
| D9 | Only v1 signatures read, so v2/v3-only APKs are reported UNSIGNED (HIGH) | `app/services/apk_parsing.py:213` |
| D10 | Website fetch identifies itself as `PARAKH-Investigation/1.0` (tips off operators, invites cloaking) | `app/services/website_analyzer.py:61` |
| D11 | The old QR result UI read `url_analysis.domain`, a field that does not exist. **The new QR verdict screen must read `url_analysis.registered_domain`** (H.2) | old `QrScanner.jsx` (removed) |
| D12 | `extract_urls` caps at 3 URLs per message | `url_intelligence.py` |

### 1.3 Library capability check (done while writing this plan)

- The installed `pyaxmlparser` **already supports** `get_certificates_der_v2()`, `get_certificates_der_v3()`, `is_signed_v2/v3()`, `get_android_manifest_xml()` and `get_intent_filters()`. **We do not need androguard.**
- Not installed yet: `phonenumbers`, `jinja2`, `pyotp`, `datasketch`, `zxing-cpp`, `asyncpg`, `alembic`, `arq`.

### 1.4 Frontend status (Revision 2, checked 24 Nov 2026)

| Item | State |
|---|---|
| `frontend/src`, `frontend/dist`, `frontend/e2e`, `node_modules` | **Removed.** `index.html` still points to `/src/main.jsx`, so `npm run dev` / `npm run build` fail and FastAPI serves no UI (`app/main.py` only mounts the SPA if `frontend/dist/index.html` exists) |
| `package.json`, `vite.config.js`, `playwright.config.js`, `.env.*` | Kept; reused in H.0 |
| New design | 31 Stitch screens (`code.html` + `screen.png`) + `civic_vigilance_light/DESIGN.md`, in `frontend/stitch_parakh_design_system/stitch_parakh_design_system/` (+ a 9.4 MB `.zip` of the same) |
| Stitch HTML technology | Static pages using the **Tailwind CDN** (`cdn.tailwindcss.com`), Google Fonts, Material Symbols, and 7 pages with hot-linked AI images (`lh3.googleusercontent.com`). None of this can ship as-is: it needs internet (breaks the offline demo), and **our own CSP (`script-src 'self'`) blocks the Tailwind CDN script** |
| Reusable old logic in git (commit `2a8e465`) | `lib/api.js`, `lib/investigateApi.js`, `lib/vault.js` (AES-GCM evidence locker), `lib/qrSafety.js` (in-browser QR decode), `lib/redaction.js` (+ tests). Use as reference implementations only: `git show 2a8e465:frontend/src/lib/vault.js` |
| Untracked backend files at risk | `app/services/campaign_service.py`, `app/api/uploads.py`, `app/data/android_permissions.py`, `tests/test_campaigns_and_citizen_apk.py`, plus `planversionalpha.md`, `wireframe.jpg`. **Commit these before anything else** (H.0 step 1) |

---

## 2. Target scores

| Dimension | Now | Target after this plan | Phase |
|---|---|---|---|
| Detection accuracy (Indian / Rajasthan threats) | 5 | **8** (measured on the golden set) | A, B |
| Security and access control | 3 | 7.5 | C |
| Evidence admissibility | 2 | 7 | E |
| Scalability | 4 | 7.5 | F |
| Data sovereignty | 3 | 7 (offline-first, AI optional and off by default) | B, C |
| Integration readiness | 1 | 4 (import/export adapters, sample formats) | D, G |
| Code quality | 8 | 9 | all |
| UI / UX (new) | 0 today (no working UI) · design quality 9 | **9**: Stitch design implemented, honest content, offline, responsive | H |
| **Hackathon overall** | 8.3 | **9+** | all |

---

## 3. Phase map

```
Phase A (measure) ──► Phase B (detection accuracy) ──────────────┐
        │                                                         │
        └──► Phase C (hierarchy + security) ──► Phase D (action layer) ──► Phase E (evidence)
                                                                  │
Phase H.0 → H.2 (frontend foundation + citizen screens) ── starts day 1, parallel to B
Phase H.3 → H.4 (citizen support + officer core screens) ─┤
Phase H.5 (officer action-layer screens, needs C/D/E APIs) ┤
                                                                  ▼
                         Phase F (scale proof) · Phase G (money trail, jurisdiction) [stretch]
                                                                  │
                                                                  ▼
                                               Phase I (demo, deck, jury)
```

**Order of work if the team is small:** A → **H.0–H.2** + B (in parallel) → H.4 → C → D + H.5 → I, then E, F, G as capacity allows. Phase B is never sacrificed, and **H.0–H.2 is not optional**: without it there is nothing to demo.

**Suggested split for a team of 3–4:**
- **Person 1 (detection):** A, B.1–B.6, B.9
- **Person 2 (APK/website + evidence):** B.7, B.8, E, then H.6 backend additions
- **Person 3 (backend workflow):** C, D, F, plus the API contracts the new screens need (H.6)
- **Person 4 (frontend + deck):** H.0–H.5, H.7, I

---

## Phase A — Measure first: golden dataset, evaluation harness, demo smoke suite (P0)

### Goal
Know our real accuracy before changing anything, so every improvement in Phase B is **measured, not claimed**. A judge or SP trusts "precision 0.93 / recall 0.88 on 420 labelled samples" far more than a feature list.

### Why
Today we have no accuracy number at all. Every rule change risks fixing one case and breaking three. The golden set is our safety net.

### Study first
- How precision, recall, F1 and confusion matrices work, and why we optimise **precision on SCAM** first (a false accusation is worse than a miss) while keeping recall acceptable.
- CERT-In advisories and state police advisories for current scam wording (e-challan APK, wedding invite APK, digital arrest, task scams).
- Dataset licences before using anything external (IEEE DataPort, Hugging Face).

### A.1 Build the golden dataset — **where:** `eval/golden/`

| File | Content | Minimum size | Hard negatives (legitimate items that look risky) |
|---|---|---|---|
| `messages.jsonl` | SMS / WhatsApp / email text: English, Hindi (Devanagari), Hinglish | 300 | ≥ 40%: genuine bank debit alerts, real OTP messages, Jio/Airtel recharge reminders, real electricity bill SMS, courier tracking |
| `urls.jsonl` | URLs | 120 | ≥ 50%: official `.gov.in` / `.nic.in` sites, bank sites, news sites with brand-like substrings (`firstpost.com`) |
| `identifiers.jsonl` | Text + expected identifier list | 80 | Version strings, order IDs, amounts, PIN codes, email addresses |
| `apks/manifest.json` | APK SHA-256 + label | 20 (10 benign, 10 malicious) | Benign apps with sensitive permissions (e.g. a real SMS app) |
| `websites/*.html` | Saved HTML pages + labels | 30 | Legitimate investment / fintech landing pages |

**Record schema (`messages.jsonl`):**
```json
{"id": "msg-0042", "text": "...", "lang": "hi|en|hinglish",
 "label": "SCAM|SUSPICIOUS|SAFE", "category": "DIGITAL_ARREST",
 "expected_identifiers": [{"type": "UPI", "value": "abc@ybl"}],
 "source": "team-written from CERT-In advisory 2025-xx | R4C | IEEE-DataPort-Hindi",
 "split": "dev|test"}
```

**Where samples come from:**
1. The R4C / organiser sample dataset (ask the organisers; DECISIONS.md open item O-2).
2. Team-written realistic messages based on published police and CERT-In advisories. Paraphrase them; never copy real victims' data.
3. Public datasets, after checking their licences:
   - [Spam SMS in Hindi Language, IEEE DataPort](https://ieee-dataport.org/documents/spam-sms-hindi-language)
   - [Hinglish & English scam text dataset, Hugging Face](https://huggingface.co/bolewara/hinglish-scam-text-dataset). This is small and partly synthetic; use it for dev only.
   - The "RevisedIndian" smishing set, cited in the [SMS phishing systematic review (arXiv 2604.11429)](https://arxiv.org/pdf/2604.11429)
4. Genuine messages from team members' own phones (bank alerts, OTPs, bills) with personal details replaced. These are the hard negatives.
5. APKs:
   - **Benign:** pulled from our own phones via `adb pull` of Play Store installs.
   - **Malicious:** [MalwareBazaar](https://bazaar.abuse.ch/), searched by tags such as `SpyNote`, `SpyMax`, `apk`.
   - **Malware handling rule:** store malicious samples only in a password-protected zip (password `infected`) outside git. Never install them. Analyse only through PARAKH's static parser.

**Split:** 70% `dev` (tune rules on these) / 30% `test` (never look at these while tuning; report final numbers only on them).

### A.2 Evaluation harness — **where:** `scripts/evaluate.py`, `tests/test_eval_gate.py`

**How it works:**
1. Run each golden item through the same code path the API uses: `RuleBasedFallbackAnalyzer`, `UrlIntelligenceService` (TLS probe off), `extract_identifiers`, `ApkAnalyzer`, `WebsiteAnalyzer.analyze_page` (on saved HTML, no network).
2. Compute:
   - per-category precision, recall and F1
   - a 3×3 confusion matrix (SCAM / SUSPICIOUS / SAFE)
   - identifier extraction precision and recall per type
   - **false-positive rate on official domains** (target: **0**)
3. Write `eval/report.md` and `eval/report.json` (committed, so progress is visible in git history).
4. **CI gate:** `tests/test_eval_gate.py` fails if test-split macro-F1 drops below the last recorded baseline minus 0.02, or if any official domain is flagged.

```text
python scripts/evaluate.py --split test --out eval/report.md
```

### A.3 Demo smoke suite — **where:** `scripts/demo_check.py`, `eval/demo_cases.json`

- About 25 exact inputs we will use on stage (the RichPlan SMS, the SBI KYC SMS, a Hindi KYC SMS, a digital-arrest message, `police.rajasthan.gov.in` as a safe URL, the QuickCash APK, a Ponzi website HTML, a genuine bank alert).
- Each has an expected verdict, category and required identifiers.
- It runs against the **live local server** over HTTP, with Gemini disabled and the network optionally disabled (`--offline`).
- Run it on every rehearsal and on demo morning. Any failure is a blocker.

### A.4 Exit criteria
- [ ] Golden set reaches the minimum sizes above, with the dev/test split frozen
- [ ] `eval/report.md` baseline recorded (expect weak numbers on Hindi and new typologies; that is the point)
- [ ] `demo_check.py` runs and reports pass/fail per case

---

## Phase B — Detection accuracy 5 → 8 (P0, the most important phase)

### Goal
Make every live detector correct on Indian and Rajasthan threats, with **zero false positives on official sites** and **no SAFE verdicts on Hindi, digital-arrest or task scams**, proven on the golden test split.

### Target metrics (test split)

| Metric | Baseline (estimate) | Target |
|---|---|---|
| Message macro-F1 (3 classes) | measure in A | ≥ 0.85 |
| SCAM precision | measure | ≥ 0.92 |
| Hindi / Hinglish SCAM recall | ~0 offline | ≥ 0.85 |
| Official-domain false positives | 5 / 6 probes | **0** |
| Identifier extraction F1 | measure | ≥ 0.90 |
| APK malicious detection (10 samples) | measure | ≥ 9/10, with 0/10 benign flagged HIGH |

---

### B.1 Text normalisation pipeline (anti-evasion) — **where:** new `app/utils/text_normalise.py`

**Problem:** scammers write `K.Y.C`, `KYC` with Cyrillic letters, zero-width spaces, `0TP`, mixed Devanagari and Latin. Our regexes only see clean English.

**Method:** produce a *normalised view* of the text for matching, **plus an index map back to the original**. Red-flag phrases must still be exact substrings of the user's message: the UI highlights them, and the AI path already enforces that.

Steps, in order:
1. Unicode **NFKC** (folds full-width and compatibility characters).
2. Strip zero-width and bidi control characters: `​-‏`, `‪-‮`, `⁠`, `﻿`.
3. **Confusable folding:** a small table based on [Unicode TR39 confusables](https://www.unicode.org/reports/tr39/) (Cyrillic `а е о р с х у і` → Latin; Greek `ο ν` → Latin), for Latin-script tokens only.
4. **Separator collapse** inside short acronyms: `K.Y.C`, `K-Y-C`, `O T P` → `KYC`, `OTP`, using the regex `\b(?:[A-Za-z][.\-_ ]){2,5}[A-Za-z]\b` (only if the collapsed token is in a known-acronym set: KYC, OTP, UPI, PIN, CVV, ATM, PAN, RBI, CBI, TRAI, NCB).
5. **Leet folding** for the matching view only: `0→o, 1→i/l, 3→e, 4→a, 5→s, @→a`, applied only to tokens that become a known keyword after folding (`0tp→otp`, `k¥c` no).
6. **Devanagari → Latin transliteration** ("romanised view"), so one Hinglish rule set matches both `khata band` and `खाता बंद`. Use [`indic-transliteration`](https://github.com/indic-transliteration/indic_transliteration_py) (pure Python) with a light post-process (drop the inherent "a", lowercase). If the library is unavailable, Devanagari keyword lists (B.3) still work.

**Index map algorithm (keeps highlights exact):**
```python
def normalise_with_map(text: str) -> tuple[str, list[int]]:
    """Return (normalised_text, index_map) where index_map[i] is the original
    index of normalised character i. Deleted characters are skipped; expanded
    characters repeat their source index."""
    out, idx = [], []
    for i, ch in enumerate(text):
        if ch in ZERO_WIDTH:            # step 2: delete
            continue
        for nch in unicodedata.normalize("NFKC", fold_confusable(ch)):
            out.append(nch); idx.append(i)
    return "".join(out), idx

def to_original_span(idx: list[int], start: int, end: int) -> tuple[int, int]:
    return idx[start], idx[end - 1] + 1
```
Rules match on the normalised view. The matched span is mapped back and the red-flag phrase becomes `original[s:e]`.

**Tests:** `tests/test_text_normalise.py`, covering `K.Y.C`, Cyrillic `КYС`, zero-width-split `O​TP`, and a Devanagari sentence round-trip mapping.

---

### B.2 Rule engine v2: evidence combination, not point-adding — **where:** `app/services/fallback_analyzer.py`, `app/data/scam_rules.py`

**Problem:** the current engine adds integer points (`score >= 55 → SCAM`). Points are arbitrary, repeated tactics double-count, and nothing is calibrated.

**Method: log-odds evidence combination** (a naive-Bayes / logistic-regression style scorer that stays fully explainable):

```
logit = bias + Σ_k  w_k · x_k          (x_k = 1 if rule k fired, after de-duplication)
p(scam) = 1 / (1 + e^(−logit))
```

- Each rule gets a weight `w_k` (log-odds contribution), stored in the rule file.
- **Tactic de-duplication:** rules sharing a `tactic_group` (e.g. URGENCY) contribute at most once (the strongest), which stops "urgent + immediately + today only" from stacking.
- **Category caps:** at most 2 rules per category count toward the score.
- **Verdict thresholds** come from the dev split: `p ≥ T_scam → SCAM`, `p ≥ T_susp → SUSPICIOUS`. Choose `T_scam` as the lowest threshold where SCAM precision on dev is ≥ 0.92.
- **Explainability:** every red flag shows its contribution ("+1.9, threat to block account"). The UI can draw this as the risk-signal map.

**How the weights are set (offline, once; no runtime dependency):**
1. In `scripts/fit_rule_weights.py`, build the binary rule-fired matrix `X` over the dev split.
2. Fit an L2-regularised logistic regression (scikit-learn, dev-time only, or a 30-line pure-Python gradient descent).
3. Clip weights to `≥ 0` for rules that are meant to indicate fraud, so a rule can never *lower* suspicion.
4. Write the weights back into `scam_rules.py` as data. Commit the fitted file and the evaluation report together.

**Rule metadata (new fields on `ScamSignalRule`):** `rule_id`, `version`, `tactic_group`, `languages`, `source` (e.g. "CERT-In advisory, Dec 2024"), `weight`. This lets reports cite exactly which reviewed rule fired.

---

### B.3 New Indian / Rajasthan typology rule packs — **where:** `app/data/scam_rules.py` (split into `app/data/rules/*.py` if it grows)

Each pack has English, Hinglish and Devanagari variants. **Do not use `\b` around Devanagari:** vowel signs (matras) are combining marks and break Python word boundaries. Use lookarounds on whitespace and punctuation instead, or no boundary at all.

| Pack | New category | Example signals (illustrative patterns) |
|---|---|---|
| Hindi KYC / account block | `KYC_SCAM` | `(?:खाता\|अकाउंट\|account).{0,30}(?:बंद\|ब्लॉक\|निलंबित\|block)`; `(?:केवाईसी\|KYC).{0,40}(?:अपडेट\|update\|लिंक)` |
| Digital arrest | **`DIGITAL_ARREST`** (new) | `digital\s*arrest\|डिजिटल\s*अरेस्ट`; `\b(?:cbi\|ed\|ncb\|narcotics\|customs\|trai\|mumbai crime branch)\b.{0,80}\b(?:arrest\|warrant\|money\s+laundering\|drugs\|parcel\|case\s+registered)\b`; `do not disconnect\|video call.{0,40}(?:statement\|verification)` |
| Task / part-time job | `FAKE_JOB` | `\b(?:rate\|review\|like)\s+(?:hotels?\|products?\|videos?\|restaurants?)\b`; `part[\s-]?time\s+(?:job\|work)`; `prepaid\s+task\|merchant\s+task`; `पार्ट\s*टाइम` |
| RTO e-challan APK | `MALICIOUS_APP` (new) | `(?:e-?challan\|traffic\s+challan\|rto).{0,60}(?:\.apk\|download\|install)`; filenames `mparivahan.*\.apk`, `rto.*challan.*\.apk` |
| Wedding-invite / PM-Kisan / reward-points APK | `MALICIOUS_APP` | `(?:wedding\|shaadi\|invitation\|निमंत्रण\|pm\s*kisan\|reward\s+points).{0,60}\.apk` |
| Rajasthan discom bills | `UTILITY_BILL_SCAM` | `\b(?:jvvnl\|avvnl\|jdvvnl\|jaipur\s+discom\|ajmer\s+discom\|jodhpur\s+discom)\b` + disconnection words; `बिजली.{0,40}(?:कट\|काट\|बंद)` |
| Jan Aadhaar / SSO ID / e-Mitra lures | `GOVERNMENT_IMPERSONATION` | `jan\s*aadhaar\|जन\s*आधार`; `sso\s*id.{0,40}(?:block\|update\|verify)`; `e-?mitra` + payment request |
| Sextortion | `SEXTORTION` (new, split from ROMANCE) | `(?:video\|photo).{0,40}(?:viral\|leak\|upload\|youtube)`; `अश्लील\|वायरल\s*कर` |
| OLX / "army officer" buyer-seller | `MARKETPLACE_FRAUD` (new) | `\b(?:army\|crpf\|bsf\|cisf)\s+(?:officer\|jawan\|man)\b.{0,80}(?:olx\|transfer\|posting\|advance\|qr)` |
| Investment / stock tips groups | `INVESTMENT_FRAUD` | `ipo\s+allotment\|institutional\s+account\|vip\s+group\|stock\s+tips` + WhatsApp/Telegram mention |
| Credit-card limit / reward points | `KYC_SCAM` | `credit\s+card.{0,40}(?:limit\|reward\s+points).{0,40}(?:redeem\|expire\|link)` |

New categories must also be added to:
- the `ScamCategory` enum (`app/schemas.py`)
- the Gemini prompt category list (`app/prompts.py`)
- `DEFAULT_ACTIONS`
- `simple_explanations.py`
- the frontend category labels

**Hard-negative guards (precision):** a small set of **legitimacy patterns** lowers the logit when present. Examples:
- a genuine bank debit-alert structure: `debited.*a/c\s*xx\d{4}.*(?:avl\s*bal\|available balance)`
- `do not share (?:this )?otp`, when no link or payment request is present

Each guard is a negative-weight rule and is tested on the hard negatives.

**Tests:** `tests/test_scam_categories.py` gets at least 3 positive cases per new pack (one per language variant) and at least 2 hard negatives per pack.

---

### B.4 URL intelligence v2 — **where:** `app/services/url_intelligence.py`, new `app/data/protected_brands.py`

**Fix D1 (false positives) and add real look-alike detection.**

1. **Trusted suffix allowlist.** `.gov.in` and `.nic.in` registrations are restricted to government bodies, so a registered domain ending in them is never brand-like. Also trust `KNOWN_BRAND_DOMAINS` ∪ `KNOWN_SITES`.
2. **Token-based brand match, not substring.** Split the host **minus the public suffix** on `[^a-z0-9]+` and match whole tokens against the brand list. Remove non-Indian noise terms (`gov`, `irs`, `usps`, `hmrc`).
   ```python
   labels = target.host.removesuffix("." + target.suffix)
   tokens = set(re.split(r"[^a-z0-9]+", labels))
   trusted = (target.registered_domain.endswith(TRUSTED_SUFFIXES)
              or target.registered_domain in KNOWN_BRAND_DOMAINS
              or target.registered_domain in KNOWN_SITES)
   if not trusted and tokens & BRAND_TOKENS:
       add BRAND_LIKE_DOMAIN
   ```
   Result: `sbi-verify-kyc.in` is still flagged (token `sbi`); `police.rajasthan.gov.in`, `firstpost.com` and `pineapple.com` are not.
3. **Typosquatting detection** (catches `sbii.co.in`, `hdfcbnak.com`, `jvvn1.in`):
   - **Optimal String Alignment distance** (Damerau-Levenshtein) between the registered-domain label and each protected label. Flag if `1 ≤ distance ≤ 2` and the label length is ≥ 4.
   - **Confusable skeleton** (TR39): compare `skeleton(label)` with `skeleton(protected)`. Flag on equality when the strings differ (`rnicrosoft` → `microsoft`).
   - Approach inspired by [dnstwist](https://github.com/elceef/dnstwist), but we *check a given domain* instead of generating permutations.
   ```python
   def osa_distance(a: str, b: str) -> int:
       d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
       for i in range(len(a) + 1): d[i][0] = i
       for j in range(len(b) + 1): d[0][j] = j
       for i in range(1, len(a) + 1):
           for j in range(1, len(b) + 1):
               cost = a[i - 1] != b[j - 1]
               d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
               if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                   d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
       return d[-1][-1]
   ```
4. **Protected brand list for Rajasthan and India** (`protected_brands.py`): banks and PSPs; `rajasthan.gov.in`, `sso.rajasthan.gov.in`, `janaadhaar.rajasthan.gov.in`, `emitra.rajasthan.gov.in`, `police.rajasthan.gov.in`; the discoms; `parivahan.gov.in`, `echallan.parivahan.gov.in`; `incometax.gov.in`, `uidai.gov.in`, `epfindia.gov.in`, `cybercrime.gov.in`. Each entry has its official domains plus the tokens to protect. **Verify every official domain by visiting it before adding it.**
5. **Suspicious TLD list refresh:** add `cyou, sbs, cfd, icu, buzz, rest, bond, top, vip, shop, live, online, site, store` as a weighted (not decisive) signal.
6. **Remove the 3-URL cap** in `extract_urls`. Analyse up to 10 URLs per message, run concurrently, with the existing per-URL timeout.
7. **Fix D6:** in `link_service.links_cases`, return `False` for any domain that is trusted (step 1) or protected (step 4). An impersonated brand's real domain is evidence of *impersonation*, not a link between operators.

**Tests:**
- `tests/test_url_intelligence.py`: official domains (≥ 30, including `police.rajasthan.gov.in`) give **no** brand signal; look-alikes (`sbi-kyc-help.cyou`, `hdfcbnak.com`, `jvvnl-bill-pay.in`) are flagged.
- `tests/test_link_service.py`: `links_cases("DOMAIN", "sbi.co.in") is False`.

---

### B.5 Identifier extractor v2 — **where:** `app/services/identifier_extractor.py`, `app/schemas.py` (`IdentifierType`)

| New / changed type | Pattern | Validation (precision) | Specificity |
|---|---|---|---|
| `TELEGRAM_BOT` (new) | `\b(\d{8,10}):([A-Za-z0-9_-]{35})\b` | Format only. Store the **bot ID** (digits) as the value and keep the token masked (`7012…aw0`) in the evidence | **120**, above PHONE (fixes D5) |
| `TELEGRAM` (extended) | `(?<![\w@.])@([A-Za-z][A-Za-z0-9_]{4,31})\b` | Accept only if `telegram\|tg\|join\|channel\|टेलीग्राम` appears within 60 chars; reject if followed by `.` + TLD (email) | 92 |
| `CRYPTO_TRON` (new) | `\bT[1-9A-HJ-NP-Za-km-z]{33}\b` | **Base58Check**: decoded payload is 21 bytes, version `0x41`, double-SHA-256 checksum matches | 96 |
| `CRYPTO_BTC` (tightened) | existing | Base58Check (version `0x00`/`0x05`) or **bech32/bech32m** checksum (BIP-173 / BIP-350) | 94 |
| `CRYPTO_ETH` | existing | Format only. EIP-55 needs Keccak-256, which is **not** `hashlib.sha3_256`, so skip unless we add a Keccak library | 96 |
| `PHONE` (rewritten) | `phonenumbers.PhoneNumberMatcher(text, "IN", leniency=VALID)` | Library validation: Indian mobiles, Indian landlines with STD codes, international numbers in E.164 | 90 |
| `IMEI` (new) | `(?<!\d)\d{15}(?!\d)` | **Luhn checksum** + an `imei\|आईएमईआई\|handset` keyword within 40 chars | 98 |
| `DOMAIN` (rewritten) | the generic host regex from `url_intelligence.URL_PATTERN` | Accept only if `tldextract` finds a **known public suffix**. This replaces the fixed TLD list, so `.cyou` and `.vip` now work | 80 |
| `IFSC` (tightened) | existing | The first 4 letters must be a known bank code (from the [razorpay/ifsc](https://github.com/razorpay/ifsc) dataset, bundled as a small code list) | 95 |
| `FIREBASE_DB` (new, mainly for APKs) | `https?://[a-z0-9-]+\.firebaseio\.com` and `[a-z0-9-]+\.firebaseapp\.com` | none | 100 |

**Checksum code (pure Python, no dependency):**
```python
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def b58check_payload(s: str) -> bytes | None:
    n = 0
    for ch in s:
        i = _B58.find(ch)
        if i < 0:
            return None
        n = n * 58 + i
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    raw = b"\x00" * (len(s) - len(s.lstrip("1"))) + raw   # leading '1' = 0x00 bytes
    if len(raw) < 5:
        return None
    payload, check = raw[:-4], raw[-4:]
    if hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] != check:
        return None
    return payload            # TRON: len 21 and payload[0] == 0x41

_BECH32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

def _polymod(values):
    gen = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    chk = 1
    for v in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            if (top >> i) & 1:
                chk ^= gen[i]
    return chk

def bech32_valid(addr: str) -> bool:
    addr = addr.lower()
    hrp, _, data = addr.rpartition("1")
    if hrp != "bc" or len(data) < 6:
        return False
    try:
        values = [_BECH32.index(c) for c in data]
    except ValueError:
        return False
    expanded = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
    return _polymod(expanded + values) in (1, 0x2BC830A3)   # bech32 / bech32m

def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0
```

**Legal and safety note on bot tokens:** PARAKH **records** a bot token as evidence. It must **never use** the token to call the Telegram API. Accessing a criminal's bot with their credential could itself be unauthorised access. Requests go to Telegram through the legal channel (Phase D).

**Tests:** extend `tests/test_identifier_extractor.py` with the probe text from Section 1.2. The bot token must be extracted as `TELEGRAM_BOT`, never as a phone. Add hard negatives: 34-character random strings starting with `T` (bad checksum), 15-digit order IDs (Luhn fail or no keyword).

---

### B.6 Identifier roles — **where:** new `app/services/identifier_roles.py`, the `identifiers` table gains a `role` column

**Problem:** the victim's number, the bank helpline the scammer impersonates, and the scammer's own UPI ID are all stored the same way, so the heat-list and links get polluted.

**Roles:** `SUSPECT`, `VICTIM`, `IMPERSONATED_BRAND`, `OFFICIAL_CONTACT`, `UNKNOWN`.

**Method (ordered rules, first match wins):**
1. Value is in the official directory (`known_sites`, `protected_brands`, `trusted_channels`, the helplines 1930/1800-xxx of known banks) → `OFFICIAL_CONTACT`.
2. Domain or package matches a protected brand's official namespace → `IMPERSONATED_BRAND`.
3. The officer marks it, or it appears in the reporter note with "my / mera / मेरा" context → `VICTIM`.
4. Payment or contact instruction context within 50 chars: `pay|send|transfer|deposit|call|whatsapp|join|भेजें|कॉल करें|जमा` → `SUSPECT`.
5. Otherwise → `UNKNOWN`.

**Effect:**
- Linking, campaigns and the heat-list use only `SUSPECT` + `UNKNOWN`.
- The officer can change a role in the case UI, and the change is audit-logged (Phase C).
- Reports show the role column.

---

### B.7 APK analyser v2 — **where:** `app/services/apk_parsing.py`, `app/services/apk_analyzer.py`, `app/data/apk_permission_rules.py`

**Study:**
- [APK Signature Scheme v2](https://source.android.com/docs/security/features/apksigning/v2) and the v3 page
- [DEX format: `string_ids` / MUTF-8](https://source.android.com/docs/core/runtime/dex-format)
- [Android AccessibilityService](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService)
- K7 Labs' [SpyMax wedding-invitation analysis](https://labs.k7computing.com/index.php/spymax-a-fake-wedding-invitation-app-targeting-indian-mobile-users/)
- the CERT-In e-challan APK advisory

**Steps:**
1. **v2/v3 signatures (fixes D9).** `pyaxmlparser` already exposes `get_certificates_der_v2()` and `get_certificates_der_v3()`. Order: v3 → v2 → v1 → META-INF fallback. Record which schemes are present (`signing_schemes: ["v2","v3"]`). `UNSIGNED_OR_UNREADABLE_SIGNATURE` fires only when **none** is found.
2. **Component-level manifest parsing (fixes D8).** Walk `apk.get_android_manifest_xml()`:
   - `<service android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE">`, or an intent filter for `android.accessibilityservice.AccessibilityService` → `ACCESSIBILITY_SERVICE_DECLARED` (HIGH)
   - `BIND_NOTIFICATION_LISTENER_SERVICE` → `NOTIFICATION_LISTENER` (HIGH; reads OTPs from notifications)
   - `<receiver>` with `android.provider.Telephony.SMS_RECEIVED` and a high `android:priority` → `SMS_INTERCEPT_RECEIVER` (HIGH)
   - `BIND_DEVICE_ADMIN` receiver → `DEVICE_ADMIN` (HIGH; blocks uninstall)
   - a request to be the default SMS app (`SMS_DELIVER` receiver) → MEDIUM
   - combination rule: accessibility + overlay + SMS receive → `BANKING_TROJAN_SIGNATURE` (CRITICAL)
3. **Fix the fixture.** `tests/apk_fixtures.py` must encode accessibility as a `<service>` with the permission attribute, the way real malware does. Keep one test proving that a uses-permission-only declaration is *not* treated as the strong signal.
4. **Proper DEX string table.** Parse `header.string_ids_off/size`, read each `string_data_item` (a ULEB128 length + MUTF-8 bytes). This is more precise than the printable-ASCII regex and catches non-ASCII strings. Keep the ASCII scan as the fallback for `assets/` and `res/raw/`.
5. **Encoded strings.** For strings matching `^[A-Za-z0-9+/]{16,}={0,2}$`, try a Base64 decode. If the decoded bytes are printable, also run them through the extractor (tag `decoded_from_base64`).
6. **C2 indicators** (high-value identifiers):
   - `api.telegram.org/bot<token>` and bare bot tokens → `TELEGRAM_BOT`
   - `*.firebaseio.com` / `firebaseapp.com` → `FIREBASE_DB`
   - hard-coded phone numbers near `sendTextMessage` / `SmsManager` strings → `SMS_FORWARD_NUMBER` finding
7. **Packer detection.** Native libraries or asset names of common Chinese and commercial packers (`libjiagu*.so`, `libsecexe.so`, `libDexHelper.so`, `libshell*.so`, `libprotectClass.so`) → a `PACKED_APP` limitation and a MEDIUM finding.
8. **Icon similarity, not just equality.** Compare the dHash Hamming distance against a **reference set of official bank/government app icons** (`app/data/reference_icons.json`, built from apps we pulled ourselves). Distance ≤ 10 combined with a package outside the brand's namespace → `ICON_IMPERSONATION` (HIGH).
9. **Split APKs.** Accept `.xapk` / `.apks` (a zip of APKs). Analyse `base.apk` and list the splits.

**Tests:** new cases in `tests/test_apk_analyzer.py`:
- a v2-only fixture is not reported as unsigned
- an accessibility `<service>` triggers the HIGH finding
- a bot token inside DEX strings yields `TELEGRAM_BOT`
- a packer `.so` adds a limitation

---

### B.8 Website analyser v2 — **where:** `app/services/website_analyzer.py`, `app/data/website_rules.py`

1. **OPSEC user-agent (fixes D10).** In officer mode, use a current mobile Chrome user-agent (scam sites target phones and cloak desktop or bot UAs). Make it configurable: `WEBSITE_FETCH_PROFILE=mobile|desktop`. Document an optional `WEBSITE_FETCH_PROXY` setting so a pilot can route through a separate egress (off by default).
2. **Phishing-kit fingerprint.** The same kit deployed on many domains is one operator. Compute:
   - `form_signature` = SHA-256 of the sorted form field names + form action path pattern
   - `script_signature` = SHA-256 of the sorted script `src` basenames
   - `favicon_hash` = SHA-256 of the favicon bytes, fetched under the same SSRF guard
   - `title_skeleton` = the title with digits and brand tokens masked

   Store `KIT_FINGERPRINT` as a linking identifier (weight 8). Research basis: kit clustering in [arXiv 2509.13186](https://arxiv.org/html/2509.13186v1), and favicon-hash hunting from [SANS ISC](https://isc.sans.edu/diary.html?date=2021-04-19).
3. **QR codes on pages.** Find `<img>` tags whose `alt`, `src` or nearby text suggests "scan" / "QR" / "pay" (at most 5 images, each ≤ 1 MB, fetched under the SSRF guard). Decode with [`zxing-cpp`](https://pypi.org/project/zxing-cpp/) (prebuilt Windows wheels). A `upi://pay?pa=` payload becomes a UPI identifier with context "UPI QR on page". If `zxing-cpp` isn't installed, add a limitation instead.
4. **Hindi website rules:** add Devanagari equivalents of guaranteed returns (`गारंटीड रिटर्न`, `रोज़ाना मुनाफ़ा`), referral (`रेफरल`, `डाउनलाइन`) and betting (`सट्टा`).
5. **Raw-bytes hash** (needed by Phase E): store `raw_sha256` of the exact HTML bytes received, separate from the normalised `content_sha256` used for dedup.

---

### B.9 AI fusion guardrail — **where:** `app/services/scam_analyzer.py`

**Problem:** when Gemini answers, its result *replaces* the rules completely. A strong rule hit can be overridden by an AI "SAFE".

**Method:** always compute the rule result. Then fuse:

| Rules | AI | Final |
|---|---|---|
| SCAM (p ≥ T_scam) | SAFE | **SUSPICIOUS**, tagged "AI and rules disagree; review" |
| SCAM | SCAM / SUSPICIOUS | AI result, plus the rule red flags merged in |
| SAFE | SCAM | AI result, tagged "AI-only signal" |
| any | unavailable | rules (current behaviour) |

The `analysis_source` tag becomes `AI`, `RULES` or `AI+RULES`, so the UI always shows honestly where the verdict came from.

---

### B.10 Citizen-path bug fixes (demo-blocking, small)
- [ ] D7 (now part of H.0): the new `frontend/src/lib/api.js` uses lowercase `/api/v1/parakh/...` paths only. Add a Playwright test for screenshot extraction (mock provider).
- [ ] D11 (now part of H.2): the new QR verdict screen reads `url_analysis.registered_domain`.
- [ ] Offline OCR fallback for screenshots: [Tesseract](https://github.com/tesseract-ocr/tesseract) with the `eng+hin` traineddata via `pytesseract`, used when Gemini is not configured. If the Tesseract binary is missing, keep the existing "paste the text" message. **Never invent text.**
- [ ] Build `frontend/dist` from the new frontend (Phase H) and confirm FastAPI serves it.

### B.11 Exit criteria for Phase B
- [ ] `eval/report.md` test split meets the target metrics table
- [ ] 0 official-domain false positives on ≥ 30 official URLs
- [ ] All probes from Section 1.2 behave correctly (each one is a unit test)
- [ ] `demo_check.py --offline` passes 100%
- [ ] Existing 274 tests still pass

---

## Phase C — Officer hierarchy, jurisdiction and security (P0)

### Goal
Replace the single shared admin account with real roles, scoped by jurisdiction, with hardened login and a tamper-evident audit log. Phase D depends on this.

### Study first
- Rajasthan Police structure: State HQ → Range (IG) → District (SP) / Commissionerate (Jaipur, Jodhpur) → Circle (DySP) → Police Station (SHO), including the district cyber police stations.
- **IT Act 2000 §78:** offences under the IT Act are investigated by an officer **not below the rank of Inspector**.
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/), sections V2 (authentication) and V3 (sessions).
- [RFC 6238 (TOTP)](https://datatracker.ietf.org/doc/html/rfc6238) for optional MFA.

### C.1 Data model — **where:** `app/db/models.py`

```text
units
  id PK · code (unique, e.g. "JPR-CYBER-PS") · name · type (STATE|RANGE|DISTRICT|CIRCLE|STATION)
  parent_id FK units · path (materialised, e.g. "/RJ/JPR-RANGE/JPR-COMM/JPR-CYBER-PS/")

users  (+ new columns)
  rank (DGP|ADG|IG|SP|ADDL_SP|DYSP|INSPECTOR|SI|ASI|HC|CONSTABLE)
  role (STATE_VIEWER|SUPERVISOR|STATION_HEAD|IO|OPERATOR|ADMIN)
  unit_id FK units · display_name · failed_logins · locked_until · totp_secret (nullable)

cases  (+ new columns)
  unit_id FK units · unit_path (copied for fast scoping) · assigned_to FK users (nullable)
  fir_no · ncrp_ack_no · offence_act (IT_ACT|BNS|BOTH|UNKNOWN)
  amount_lost (int, paise) · victim_count (int, default 1) · priority (P1|P2|P3)

audit_events
  id PK · seq (unique, increasing) · at · actor_id · actor_role · action · target_type · target_id
  details JSON · prev_hash · entry_hash
```

**Why a materialised path:** "everything under my unit" becomes one indexed prefix query, `cases.unit_path LIKE :user_path || '%'`. No recursive queries are needed, and it works the same on SQLite and Postgres.

**Schema creation:** we still use `create_all`. Add a `scripts/reset_demo_db.py` that drops and re-seeds. Phase F introduces Alembic.

### C.2 Role → permission matrix — **where:** new `app/core/permissions.py`

| Permission | OPERATOR | IO | STATION_HEAD | SUPERVISOR | STATE_VIEWER | ADMIN |
|---|---|---|---|---|---|---|
| Submit artifact / create case | ✓ | ✓ | ✓ | ✓ | – | – |
| View cases in own unit subtree | own submissions | assigned + own station | station | district subtree | state (read-only) | all |
| Assign / transfer case | – | – | ✓ | ✓ | – | – |
| Draft documents (Phase D) | – | ✓ | ✓ | ✓ | – | – |
| Approve station level | – | – | ✓ | ✓ | – | – |
| Approve supervisor level | – | – | – | ✓ | – | – |
| Full (unredacted) export | – | ✓ (own cases) | ✓ | ✓ | – | – |
| Manage users / units | – | – | – | – | – | ✓ |

Implement this as a dependency, `require_permission("case.assign")`, plus a `scope_cases(query, user)` helper applied inside `case_service._apply_filters`, `link_service` and `campaign_service`. **Every read path must be scoped, or data leaks across districts.** Add a test per endpoint: an officer from station A gets 404 for a case in station B.

### C.3 Business rules
- **IT Act §78 rule:** if `offence_act ∈ {IT_ACT, BOTH}`, `assigned_to.rank` must be ≥ INSPECTOR. Otherwise the assignment is refused with that explanation.
- **Transfer:** the SHO transfers a case to another unit with a mandatory reason. `unit_id` and `unit_path` change, and the history is kept in `audit_events`.
- **Citizen reports:** they land in the station chosen by the citizen's district (a dropdown on the report form), or in a district "unassigned" queue.

### C.4 Login hardening — **where:** `app/api/investigate.py`, `app/core/auth.py`
- **Rate-limit login** per username and per IP. After 5 failures, lock for 15 minutes, doubling up to 4 hours (`locked_until`). Use the same generic error message.
- **Optional TOTP MFA** ([`pyotp`](https://github.com/pyauth/pyotp)), required for SUPERVISOR and ADMIN in the demo seed. The QR code for enrolment is shown once.
- Token TTL drops to 8 hours, plus "sign out all sessions".
- **Fix rate-limit spoofing:** `trust_proxy_headers` defaults to `False` (`app/config.py:50`).
- **Fix CORS** (`app/main.py:114`): allow `PATCH` and the `Authorization` header, for configured origins only.
- **Citizen-report quarantine:** cases with `source=CITIZEN` count toward the heat-list and the "Already seen in police cases" check only after an officer sets `verified=true`.

### C.5 Tamper-evident audit log — **where:** new `app/services/audit_service.py`

**Algorithm (hash chain):**
```python
def append_event(session, actor, action, target_type, target_id, details):
    last = session.scalar(select(AuditEvent).order_by(AuditEvent.seq.desc()).limit(1))
    prev_hash = last.entry_hash if last else "0" * 64
    seq = (last.seq + 1) if last else 1
    body = json.dumps({"seq": seq, "at": utcnow_iso(), "actor": actor.id, "action": action,
                       "target": [target_type, target_id], "details": details},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    entry_hash = hashlib.sha256((prev_hash + body).encode("utf-8")).hexdigest()
    session.add(AuditEvent(seq=seq, ..., prev_hash=prev_hash, entry_hash=entry_hash))

def verify_chain(events) -> int | None:
    """Return the seq of the first broken link, or None if intact."""
```
- **Logged actions:** login, login_failed, case.view, case.create, case.update, case.assign, case.transfer, identifier.role_change, document.* (Phase D), export.full, export.redacted.
- **Concurrency:** SQLite serialises writes anyway. On Postgres, wrap the append in `pg_advisory_xact_lock(<constant>)`.
- **UI:** a "Who did what, when" timeline on each case, plus an admin page showing **"Audit chain: verified ✓ (N events)"**, computed live.

### C.6 Demo seed — **where:** extend `app/db/demo_seed.py`
- Units: `RJ` → `JPR-RANGE` → `JPR-COMM` → `JPR-CYBER-PS`, `JPR-SOUTH-PS`, plus `BTP-DISTRICT` → `BTP-CYBER-PS` (to show scoping).
- Users (demo passwords set from `.env`):

  | Username | Rank | Role | Unit | MFA |
  |---|---|---|---|---|
  | `sp.jaipur` | SP | SUPERVISOR | JPR-COMM | on |
  | `dysp.cyber` | DySP | SUPERVISOR | JPR-COMM | – |
  | `sho.cyber` | Inspector | STATION_HEAD | JPR-CYBER-PS | – |
  | `io.si.sharma` | SI | IO | JPR-CYBER-PS | – |
  | `op.hc` | HC | OPERATOR | JPR-CYBER-PS | – |
  | `io.btp` | Inspector | IO | BTP-CYBER-PS | – |

  These are role labels, not real people.
- Existing demo cases are assigned to Jaipur units; two Bharatpur cases demonstrate scoping.

### C.7 Exit criteria
- [ ] Scoping tests pass for every investigate endpoint (cross-unit access gives 404)
- [ ] §78 assignment rule tested
- [ ] Lockout and TOTP tested
- [ ] `verify_chain` detects a manually edited audit row (test)
- [ ] The UI shows a different dashboard per role

---

## Phase D — Action layer: action pack, approval chain, dispatch, MIS (P1)

### Goal
Turn detection into action: auto-drafted legal requisitions from extracted identifiers, an approval chain that follows the chain of command, dispatch and response tracking, and one-click reports to seniors.

### Study first (talk to people, not only websites)
- **Visit or call one cyber police station.** Ask for redacted sample formats of: a notice to a bank (KYC/statement), a freeze/lien request, a request to a telecom operator for CAF/CDR, a takedown request, and the §63 certificate they use. Ask how long a typical notice set takes today. **That measured number goes on the slide.**
- Laws to read (bare acts on [India Code](https://www.indiacode.nic.in/)):
  - **BNSS 2023 §94** (summons to produce documents, formerly CrPC §91)
  - **BNSS 2023 §106** (seizure, formerly CrPC §102, used for freezes)
  - **IT Act 2000 §79(3)(b)** (intermediary takedown)
  - **BSA 2023 §63** (electronic evidence certificate)
- Portals: Sahyog (MHA, for intermediary takedown notices), DoT Sanchar Saathi / Chakshu (reporting fraud numbers), CFCFRMS.
- Write `docs/legal_notes.md` with what we confirmed and who confirmed it. Anything unconfirmed stays labelled DRAFT.

### D.1 Data model — **where:** `app/db/models.py`

```text
documents
  id PK · doc_no (e.g. "PRK/JPR-CYBER/2026/0142") · case_id FK · doc_type
  addressee_key · addressee_display · subject_identifier (type:value)
  status · version · body_html · body_sha256 · created_by · created_at
  current_stage (STATION|SUPERVISOR|NONE) · due_at · dispatched_at · dispatch_ref · dispatch_channel
  response_received_at · response_note

document_versions   (document_id, version, body_html, body_sha256, edited_by, at)
approvals           (document_id, stage, actor_id, action APPROVE|RETURN, comment, body_sha256, at)
addressees          (key, org_name, org_type BANK|PSP|TELECOM|REGISTRAR|HOSTING|PLATFORM|DOT,
                     channel EMAIL|PORTAL|POST, contact_placeholder, notes, is_sample)
```

### D.2 Addressee resolution — **where:** new `app/services/addressee_resolver.py`, `app/data/addressees.py`

| Identifier | Resolution method | Result |
|---|---|---|
| `UPI` `x@ybl` | Static handle → PSP and sponsor-bank map (`ybl`, `ibl`, `axl` → PhonePe/partner banks; `okaxis`, `okhdfcbank`, `oksbi`, `okicici` → Google Pay/partner bank; …). Mark each mapping "verify". Handle–bank partnerships change, so the officer confirms | "Nodal Officer, <PSP> / <sponsor bank>" |
| `BANK_ACCOUNT` + `IFSC` | IFSC first 4 letters → bank; full IFSC → branch, district (bundled [razorpay/ifsc](https://github.com/razorpay/ifsc) subset) | "Nodal Officer, <Bank>", with branch and district shown |
| `PHONE` (Indian mobile) | `phonenumbers.carrier.name_for_number()` gives the **originally allocated** operator. Show "may have been ported (MNP); confirm" | "Nodal Officer, <Operator>"; plus a DoT Chakshu report |
| `DOMAIN` | RDAP (already fetched): registrar name, plus the **abuse contact** from RDAP entities with role `abuse` (RFC 9083 vCard). Cached in `domain_intel` | Registrar abuse desk (real contact from RDAP, so not hardcoded) |
| `IP` | RDAP for IP (`https://rdap.org/ip/<ip>`): network owner + abuse contact | Hosting provider abuse desk |
| `TELEGRAM` / `TELEGRAM_BOT` / WhatsApp | Platform | Sahyog portal submission content (generated text, manual upload) |
| `PACKAGE` | Platform | Google Play takedown request text |

Sample addressees are marked `is_sample=true`, and the UI shows a "sample contact — replace with official nodal contact" badge. No invented emails.

### D.3 Templates — **where:** `app/templates/documents/*.html.j2` (Jinja2 with autoescape on)

| `doc_type` | Generated from | Key fields |
|---|---|---|
| `BANK_PRODUCE_94` | UPI / account | account or VPA, period, required records (KYC, statement, linked accounts, device/IP logs, beneficiary details) |
| `BANK_FREEZE_106` | UPI / account | amount, victim transaction UTRs, time, request to hold the disputed amount |
| `TELECOM_CAF_CDR` | phone | number, period, CAF, CDR, IMEI linked |
| `DOT_CHAKSHU_REPORT` | phone / IMEI | number, fraud type, evidence summary |
| `REGISTRAR_TAKEDOWN` | domain | domain, registrar, evidence URLs, request for suspension and registrant data |
| `HOSTING_ABUSE` | IP | IP, URLs hosted |
| `INTERMEDIARY_79_3B` | Telegram / WhatsApp / app | handles / channels / package, unlawful content description |
| `BSA_63_CERT` | any evidence | evidence list with SHA-256, system description, capture time (Part A); Part B left for the expert |
| `CASE_SUMMARY` | case | the existing report, now with officer name, rank and unit |

Every template:
- has a header block (unit, doc no., date) and a footer (signature block for the approving officer)
- carries a **"DRAFT — for officer review"** watermark until approved
- puts the case's evidence hashes in an annexure

### D.4 "Generate action pack" — **where:** `app/services/document_service.py`

**Algorithm:**
1. Take the case's identifiers with role `SUSPECT` or `UNKNOWN` (from B.6).
2. Group them by `(doc_type, addressee_key)`. For example, two UPI IDs on the same PSP produce **one** notice with both IDs.
3. For each group, render the template and create a document with status `DRAFT` and version 1, storing `body_sha256`.
4. Always add a `BSA_63_CERT` draft for the case evidence.
5. Return the list. The UI shows the cards with addressees.

**Idempotency:** regenerating skips groups that already have a non-cancelled document. "Regenerate" creates a new version, not a duplicate.

### D.5 Approval state machine — **where:** `app/services/workflow_service.py`

```
DRAFT ──submit──► PENDING_STATION ──approve──► (needs supervisor?) ──yes──► PENDING_SUPERVISOR ──approve──► APPROVED
  ▲                    │                              │ no                         │
  └──────return────────┴──────────────return──────────┴────────────────────────────┘
APPROVED ──dispatch(ref, channel)──► DISPATCHED ──record_response(note, file)──► RESPONDED ──close──► CLOSED
any non-final ──cancel(reason)──► CANCELLED
```

**Policy table** (data, editable): `app/data/approval_policy.py`

| doc_type | Station approval | Supervisor approval | SLA per stage |
|---|---|---|---|
| BANK_FREEZE_106 | ✓ | ✓ (always) | 2 h (golden hour) |
| BANK_PRODUCE_94 | ✓ | if case `amount_lost` ≥ ₹10 lakh | 24 h |
| TELECOM_CAF_CDR | ✓ | – | 24 h |
| REGISTRAR_TAKEDOWN / INTERMEDIARY_79_3B | ✓ | ✓ | 24 h |
| BSA_63_CERT | ✓ | – | 48 h |

**Rules enforced in code:**
- Only the role for the current stage, within the document's unit subtree, can approve.
- **The drafter cannot approve their own document** (separation of duties).
- RETURN requires a comment.
- Editing after a return creates a new version. Approvals record the `body_sha256` they approved, so a document edited after approval is detectably different.
- Every transition writes an `approvals` row **and** an `audit_events` entry.

**Escalation, without a cron job:** `overdue = now > due_at`, computed on read. The queue sorts overdue items first and shows them in red. The supervisor's dashboard shows "overdue at station level" counts per station. An optional background sweep can come in Phase F.

### D.6 APIs — **where:** new `app/api/documents.py`

```
POST /investigate/cases/{case_id}/action-pack        → generate drafts
GET  /investigate/queue                              → items waiting for *me*, overdue first
GET  /investigate/documents/{id}                     → document + versions + approvals
PUT  /investigate/documents/{id}                     → edit (DRAFT/RETURNED only)
POST /investigate/documents/{id}/submit|approve|return|dispatch|response|cancel
GET  /investigate/documents/{id}/print               → print-ready HTML (A4)
POST /investigate/cases/{case_id}/assign             → {officer_id}  (§78 check)
POST /investigate/cases/{case_id}/transfer           → {unit_id, reason}
GET  /investigate/reports/mis?period=daily|weekly    → MIS HTML/JSON
GET  /investigate/audit/verify                       → chain status (ADMIN/SUPERVISOR)
```

### D.7 MIS report to seniors — **where:** `app/services/mis_service.py`

One query set per period, scoped to the user's unit subtree:
- cases received by artifact type, risk and source
- cases assigned versus unassigned
- notices drafted, approved, dispatched and responded; overdue by stage
- amount reported lost; amount whose freeze request has been dispatched (from documents)
- top 10 new `SUSPECT` identifiers; active campaigns with case count and total loss

Rendered as a printable HTML page (same styling as `report_builder.py`) plus JSON. The numbers are computed live from the data, never hardcoded.

### D.8 Frontend — **where:** `frontend/src/features/officer/` (built with the Phase H kit; designs generated per H.5)
- `QueuePage.jsx`: "My queue", grouped by stage, with SLA badges.
- `DocumentPage.jsx`: preview, edit (rich text or a simple textarea is fine), version diff, approval timeline, action buttons per role.
- Case detail additions: an "Generate action pack" button, an assignment dropdown, a transfer dialog, a role chip per identifier, and an audit timeline.
- `MisPage.jsx` and a units/users admin page (ADMIN only).

### D.9 Exit criteria
- [ ] Action pack for the RichPlan case produces the expected documents (snapshot test)
- [ ] State-machine tests cover every transition, the separation-of-duties rule, the RETURN-needs-comment rule, and the approval hash check
- [ ] Three-login demo flow works in the browser: IO → SHO (approve 3, return 1) → SP (approve freeze) → dispatched → audit timeline
- [ ] MIS report numbers match a hand-count on the demo seed

---

## Phase E — Evidence integrity and court readiness (P1)

### Goal
Make every case's evidence defensible: original bytes preserved, hashed at capture, custody logged, certificate drafted, and gaps visible before charge-sheet.

### Study first
- **BSA 2023 §63:** the certificate requirements and the Part A / Part B structure.
- [RFC 3161](https://datatracker.ietf.org/doc/html/rfc3161) (trusted timestamps).
- [WARC, ISO 28500](https://iipc.github.io/warc-specifications/) and [`warcio`](https://github.com/webrecorder/warcio).

### E.1 Evidence store — **where:** new `app/services/evidence_store.py`, folder `evidence_store/` (gitignored)
- Store originals: APK bytes (officer mode), raw website HTML bytes + response headers, raw `.eml`, the original message text as UTF-8 bytes.
- Path `evidence_store/<case_id>/<sha256>.<ext>`, content-addressed, **write-once** (never overwrite; refuse if it exists with different bytes).
- A new `evidence_items` table: case_id, kind, filename, size, sha256, sha512, captured_at, captured_by, capture_method (e.g. "PARAKH guarded fetch v2, mobile UA, no JS"), source_url, notes.
- Citizen mode still stores nothing unless the citizen consents to "Report to police" (ADR-001 test stays green).

### E.2 Web capture (optional, best demo value)
- Write a WARC of the fetch with `warcio`: request, response and headers.
- An optional full-page screenshot via Playwright (it's already a frontend dev dependency; install `playwright` for Python + Chromium). Run it **in a separate worker process with a timeout**, never in the API process. If unavailable, record a limitation.
- Optional RFC 3161 timestamp from a configured TSA (off by default for sovereignty). With no TSA, use the audit chain timestamp.

### E.3 Certificate, bundle and checklist
- `BSA_63_CERT` (Phase D template), auto-filled from `evidence_items`.
- **Evidence bundle:** `GET /investigate/cases/{id}/bundle.zip` containing originals, `manifest.json` (file → SHA-256/512, capture metadata), the case report, the §63 certificate draft, and an audit extract. The manifest's own SHA-256 is shown in the UI and written to the audit log.
- **Chargesheet-readiness checklist** (computed live, shown on the case):
  - IO assigned (rank OK under §78)
  - FIR / NCRP number recorded
  - evidence hashed
  - §63 certificate approved
  - bank response received for every suspect account
  - CAF received for every suspect number
  - takedown status known
  - accused identified (a manual tick)

  Shown as "6 / 9 ready", with links to the missing items.
- **Remove the hidden watermarks** from reports (`_WM`, `x-sig`, `_BUILD_SIG`). Put authorship in `LICENSE` / README. Hidden characters in an evidence document can be challenged in court.

### E.4 Exit criteria
- [ ] Bundle reproducibility: recompute hashes of the extracted bundle and compare with the manifest (test)
- [ ] Write-once store refuses overwrite (test)
- [ ] Checklist reflects document states from Phase D

---

## Phase F — Scalability 4 → 7.5 (P2)

### Goal
Prove that PARAKH can handle state-level volume. The demo stays on SQLite for reliability; scale is shown on Postgres with a load-test report.

### Correction to an earlier recommendation
Splitting the 64-bit SimHash into **4 bands of 16 bits** only guarantees finding pairs with Hamming distance **≤ 3** (pigeonhole principle: with 4 bands, at most 3 differing bits can leave one band untouched). Our near-duplicate threshold is **16 bits**, and to guarantee that we'd need ≥ 17 bands of about 4 bits each, which gives almost no filtering. So for candidate generation we use **MinHash LSH** instead.

### F.1 Postgres profile — **where:** `docker-compose.yml`, `app/config.py`
- `DATABASE_URL=postgresql+asyncpg://…`. The models are already ORM-only. Add `asyncpg`.
- Introduce **Alembic** (`alembic/`) with a baseline migration of the current schema plus Phases C–E.
- Indexes:
  - `CREATE EXTENSION pg_trgm;`
  - GIN trigram indexes on `cases.content_text`, `cases.summary` and `identifiers.value` ([pg_trgm docs](https://www.postgresql.org/docs/current/pgtrgm.html))
  - B-tree on `(identifiers.type, identifiers.value)`, `cases.created_at`, `cases.unit_path text_pattern_ops` (prefix scoping)
- The search code uses `ILIKE` on Postgres, which the trigram index accelerates. SQLite keeps `LIKE`.

### F.2 Incremental campaigns — **where:** `app/services/campaign_service.py`
- New table `campaign_members(case_id PK, campaign_id)`, plus a `campaigns` table (id, name, first_seen, last_seen, case_count, total_loss, risk).
- **On case creation:** look up existing cases sharing any linking identifier (indexed) plus LSH candidates (F.3). Gather their campaign IDs. If there are none, start a new campaign. If there are several, **merge** them (keep the oldest ID, re-point members). This is union-find persisted in the database.
- The campaign page reads stored campaigns. A full rebuild command (`scripts/rebuild_campaigns.py`) exists for consistency checks.
- **Optional quality step:** for very large components, run Louvain community detection ([`networkx.community.louvain_communities`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html)) to suggest a split when one hub merges unrelated groups. Suggest only; never split automatically.

### F.3 MinHash LSH for near-duplicates — **where:** `app/utils/fingerprint.py`
- MinHash with 100 permutations over the same character 5-gram shingles, stored as an array or blob per case.
- **Banding: b = 20 bands × r = 5 rows.** The probability that a pair becomes a candidate is `1 − (1 − s^5)^20`, giving a threshold of about `(1/20)^(1/5) ≈ 0.55` Jaccard similarity.
- Store `lsh_bands(case_id, band_no, band_hash)` with an index on `(band_no, band_hash)`. Candidates are the cases sharing any band. Then **verify** with the existing SimHash distance ≤ 16 (keeps current behaviour and tests).
- Library option: [`datasketch`](https://github.com/ekzhu/datasketch), or a ~40-line implementation in our own code (preferred; no numpy).
- Theory: Broder (1997), *On the resemblance and containment of documents*; Leskovec, Rajaraman & Ullman, *Mining of Massive Datasets*, ch. 3 ([free book](http://www.mmds.org/)).

### F.4 Background jobs — **where:** `app/workers/`, [`arq`](https://arq-docs.helpmanual.io/) + Redis
- APK, website, media and evidence-capture jobs run in workers. The API returns `202 {job_id, case_id}` and the UI polls `GET /investigate/jobs/{id}` (or uses SSE).
- **Keep a synchronous fallback** (`JOBS_MODE=inline`) so the demo laptop works without Redis.

### F.5 Load test — **where:** `scripts/generate_synthetic_cases.py`, `loadtest/locustfile.py` ([Locust](https://locust.io/))
- Generate 1,00,000 synthetic cases with realistic identifier reuse (Zipf-distributed popularity) and 200 planted campaigns.
- Measure p50 / p95 for: case search, identifier pivot, case detail, campaign page, heat-list, and case creation at 20 concurrent users.
- Publish `docs/loadtest.md` with the hardware used and the numbers. **Only measured numbers go on slides.**

### F.6 Exit criteria
- [ ] Alembic migrations apply cleanly on empty Postgres
- [ ] Incremental campaign IDs equal those from a full rebuild on the synthetic set
- [ ] LSH recall ≥ 0.95 versus a brute-force scan on a 5,000-case sample (test)
- [ ] Load-test report committed

---

## Phase G — Intelligence extensions: money trail, jurisdiction intelligence (P2)

### G.1 Campaign loss and victim count (small, high value; do it first)
- Sum `amount_lost` and `victim_count` per campaign. Rank campaigns by `total_loss × log(1 + victims) × recency`.
- Show it on the campaign list and in the MIS report: "One investigation per campaign, not per complaint."

### G.2 Golden-hour money trail — **where:** new `app/services/money_trail.py`, `transactions` table

**Data entry:**
- victim transactions (UTR, amount, timestamp, from-account, to-VPA/account), entered manually or imported from CSV
- bank replies (a statement CSV in a documented sample format)

```text
transactions(id, case_id, utr, ts, amount_paise, from_key, to_key, source VICTIM|BANK_REPLY|MANUAL)
account keys: "UPI:x@ybl", "ACC:<ifsc>:<number>"
```

**Algorithm: FIFO taint propagation.** FIFO follows the *Clayton's Case* rule, which Anderson, Shumailov & Ahmed propose for tracing stolen funds in *Making Bitcoin Legal* (Security Protocols Workshop, 2018).
```text
for each account: queue of (amount, victim_id, credited_at)
process all transactions in timestamp order:
  credit from a victim → push (amount, victim, ts) to the receiver's queue
  debit A→B of x       → pop from A's queue FIFO until x is covered;
                         push the popped portions (same victim labels) to B's queue
remaining_taint(A) = Σ amounts left in A's queue
```

**Freeze-priority score** (explainable, shown with its parts):
```text
priority(A) = remaining_taint(A)
            × e^(−hours_since_last_credit / τ)      # τ = 6 h: money moves fast
            × (1 + ln(1 + distinct_victims(A)))
            × layer_weight(A)                        # L1 = 1.0, L2 = 0.9, L3+ = 0.8 (recovery is harder deeper down)
```

**Output:**
- a layered graph (reusing `CampaignGraph.jsx` with an L1→L2→L3 layout)
- a ranked "freeze now" list
- one click on an account → `BANK_FREEZE_106` draft (Phase D)

**Honesty note:** this is decision support built on the data entered. It is not proof of where specific money went.

### G.3 Jurisdiction and origin intelligence — **where:** `app/services/geo_intel.py`
- IFSC → branch district (bundled razorpay dataset, Rajasthan + neighbouring states subset).
- Phone → originally allocated operator (`phonenumbers.carrier`). Telecom circle only if a reliable number-series dataset is added; otherwise show the operator only.
- IP → RDAP network owner and country.
- Victim district from the case.
- UI:
  - a district choropleth (cases by victim district)
  - an origin table ("money landed in accounts from branches in district X")
  - **suggested routing** of new cases to the station with jurisdiction (the SHO confirms)
- **Framing rule:** attribute *infrastructure* (accounts, SIMs, servers), never communities. Show counts, not labels such as "criminal village".

### G.4 Integration adapters (readiness, no live access needed) — **where:** `app/integrations/`
- `ncrp_import.py`: import a CSV/XLSX with a documented sample column layout → cases + transactions.
- `export_cctns.py`: a case summary in a structured JSON/CSV layout for manual entry or future API.
- `export_stix.py`: identifiers as [STIX 2.1](https://oasis-open.github.io/cti-documentation/) indicators for sharing with CERT-In / I4C.
- Each adapter is an interface with a file-based implementation. A real API adapter can replace it after official approval.

---

## Phase H — New frontend: implement the Stitch design system and wire it to the backend (P0, runs in parallel)

### Goal
Turn the 31 static Stitch screens into **one working React app**:
- the same look (Civic Vigilance Light, light theme only)
- every number and verdict coming from the real backend
- runs **fully offline** on the demo laptop
- served by FastAPI from `frontend/dist`
- no fake claims anywhere on screen

### Why this is P0
There is no working UI today (Section 1.4). The analysers, linking and reports only count for the jury if they can be shown. The Stitch designs are visually strong, but they are **mock-ups**: static HTML, CDN-loaded, full of invented numbers and some claims we cannot make. Shipping them as-is would break three of our own rules: the offline demo (0.2), honesty (0.1), and the CSP in `app/core/middleware.py`.

### Study first
- `civic_vigilance_light/DESIGN.md`: the token source of truth (colours, type scale, radii, elevation, identifier colours, risk tri-signal rule).
- Tailwind v4 `@theme` and `@utility` ([docs](https://tailwindcss.com/docs/theme)). The Stitch pages use the **v3 CDN `tailwind.config`** format, so the tokens must be translated, not copied.
- React Router v7 data routes, TanStack Query (server state with loading/empty/error), Framer Motion `useReducedMotion`.
- `d3-geo` + `topojson-client` for the maps; [mapshaper](https://mapshaper.org/) to simplify boundary files.
- WCAG 2.1 AA and GIGW 3.0 basics (contrast, focus, labels, Hindi `lang` attributes).

---

### H.0 Foundation (do first; everything else depends on it)

**Step 1: protect what exists.** Commit the untracked backend files (`campaign_service.py`, `uploads.py`, `android_permissions.py`, `test_campaigns_and_citizen_apk.py`), `planversionalpha.md` and `wireframe.jpg`. Add `frontend/stitch_parakh_design_system.zip` to `.gitignore` (the extracted folder is enough). Move the Stitch folder to `design/stitch/` so it is clearly *reference*, not app code (keep paths in this plan updated).

**Step 2: scaffold.** Reuse `package.json` / `vite.config.js` (React 19, Vite, Tailwind v4 via `@tailwindcss/vite`, react-router-dom, framer-motion), then:
```text
npm install
npm install @tanstack/react-query d3-geo topojson-client d3-force \
  @fontsource-variable/plus-jakarta-sans @fontsource/noto-sans-devanagari \
  @fontsource-variable/jetbrains-mono material-symbols
npm install -D vitest @testing-library/react @testing-library/user-event jsdom @playwright/test
```
Remove `lucide-react` once every icon uses Material Symbols, so there's one icon system and it matches the designs.

**Step 3: tokens.** Write `frontend/src/design/tokens.css`:
- **Colours from DESIGN.md:**
  - surfaces: `--color-canvas` `#F7F8FB`, `--color-sand` `#FBF7F1`, `--color-card` `#FFFFFF`
  - primary: `#1D4ED8` / hover `#1E40AF`; accent `#E07A2F` / hover `#C2410C`
  - Stitch Material tokens such as `--color-primary-container` and `--color-surface-container-*`, so classes copied from the Stitch HTML keep working
- **Risk tri-signal:** high `#DC2626` on `#FEF2F2`, medium `#D97706` on `#FFFBEB`, low `#059669` on `#ECFDF5`.
- **12 identifier colours:** `--color-id-upi` `#7C3AED`, `--color-id-phone` `#2563EB`, `--color-id-bank` `#B45309`, `--color-id-ifsc` `#A16207`, `--color-id-domain` `#0D9488`, `--color-id-url` `#475569`, `--color-id-email` `#0891B2`, `--color-id-telegram` `#0284C7`, `--color-id-ip` `#E11D48`, `--color-id-crypto` `#EA580C`, `--color-id-package` `#4F46E5`, `--color-id-cert` `#6D28D9`.
- **Type scale as `@utility`:** `text-display-hero` 44/52/800, `text-headline-lg` 32/40, `text-headline-md` 24/32, `text-headline-sm` 20/28, `text-title-md` 16/24, `text-body-lg` 18/28, `text-body-md` 15/22, `text-body-sm` 13/18, `text-label-ui` 12/16/600 +0.04em, `text-mono-md`, `text-mono-sm`, plus the mobile variants. Devanagari spans get a `.hi` class at **1.05×** size with Noto Sans Devanagari.
- **Radius / elevation:** chip and input `10px`, card `16px`, hero `24px`; shadows L1–L3 and glass (`rgba(255,255,255,.78)` + 16px blur) exactly as DESIGN.md.
- **Tabular numerals:** `font-feature-settings:'tnum'` on tables, KPIs and timestamps.

**Step 4: fonts and icons, self-hosted.** Import the `@fontsource` packages and `material-symbols/outlined.css` in `main.jsx`. Then:
- Remove every `fonts.googleapis.com` / `cdn.tailwindcss.com` reference.
- Tighten the CSP in `app/core/middleware.py` (drop the Google Fonts domains), and test it.

This also fixes the inconsistency found in review: several Stitch pages have no `fontFamily` config and render in a **serif fallback** (analysing, APK, check, rescue, help, QR, learn and all verification pages).

**Step 5: app shell and plumbing.** Build these in `frontend/src/`:

| Module | Purpose |
|---|---|
| `app/router.jsx` | All routes (table in H.2–H.5); citizen bundle and officer bundle code-split with `React.lazy` so citizens never download officer code |
| `app/CitizenLayout.jsx` | Top nav from the Stitch citizen pages (Check · App check · Learn · Evidence · Help · Rescue), EN/हिंदी toggle, red **1930 Helpline** pill, officer-login link; on < 768 px the **bottom tab bar** from the mobile designs (Home · Check · Apps · Learn) |
| `app/OfficerLayout.jsx` | Left sidebar from the Stitch officer pages + top bar (search with identifier auto-detect, date range, notifications, "+ New Forensic Analysis"); sidebar items filtered by role (Phase C) |
| `lib/api.js` | One fetch client, base `/api/v1`, **lowercase paths only** (D7), JSON errors → typed `ApiError`, bearer token for officer routes, 401 → logout |
| `lib/queries/*.js` | TanStack Query hooks per endpoint (`useAnalyseMessage`, `useCase(id)`, `useHeatlist(filters)` …) so loading/empty/error states are uniform |
| `lib/i18n.jsx` | Small dictionary context (`en.json`, `hi.json`) + `t()`; bilingual headings stay as designed; the toggle switches body copy; choice saved in `localStorage` |
| `lib/identifiers.js` | Client-side detection for live chips and the officer search box. It must mirror `app/services/identifier_extractor.py` patterns, and is checked by a shared test-vector file `tests/fixtures/identifier_vectors.json` used by both pytest and Vitest |
| `lib/vault.js`, `lib/qr.js`, `lib/redaction.js` | Port from git commit `2a8e465` (evidence locker AES-GCM, browser QR decode, redaction) |
| `design/ui/*` | Component kit (below) |

**Step 6: component kit (`frontend/src/design/ui/`).** Build these once and reuse everywhere. Each one is taken from a Stitch screen.

| Component | Taken from | Notes |
|---|---|---|
| `Button` (primary, citizen-accent, ghost, danger) | all | 10 px radius, focus ring per DESIGN.md |
| `IdentifierChip` | check, result, case detail, heat-list | type colour + mono value + copy button + optional "seen in N cases" badge |
| `RiskBadge`, `RiskCard` | result pages, case table | always colour **+ icon + text** |
| `RiskGauge` (semicircle) | result high/low, APK, QR | animated sweep; `aria-label="Risk 92 of 100"` |
| `SignalMap` (radial) | result pages | built from real findings and weights, not decorative |
| `Stepper` / `PipelineProgress` | analysing, ingestion, case status | |
| `Timeline` | campaign evolution, audit trail, rescue checklist | |
| `DataTable` | dashboard, heat-list, case table | sticky header, mono columns, row hover `#FBF7F1`, reflows to cards < 768 px |
| `KpiCard` + `Sparkline`, `Donut`, `AreaTrend` | dashboard, heat-list | own small SVG charts (no chart library) |
| `StateBlock` (empty, loading skeleton, error + retry) | the five `*_empty_loading_error_states` screens | one component, used by every data view |
| `Segmented`, `Tabs`, `Modal`, `Drawer`, `Toast`, `Tooltip`, `ConsentCheckbox`, `FileDrop` | various | |
| `IndiaMap`, `RajasthanDistrictMap` | home hero, dashboard choropleth | see H.7 |
| `NetworkGraph` | campaign map, case-detail linked graph | `d3-force` with a fixed seed and fixed iteration count, so the same data always gives the same layout |

**Step 7: conversion workflow (per screen).**
1. Open the screen's `code.html`. Copy the `<body>` markup into a new `.jsx` file.
2. Convert: `class`→`className`, `for`→`htmlFor`, self-close void tags, `style="…"` → objects. A converter such as `htmltojsx` speeds this up; review by hand.
3. Replace repeated blocks with kit components (chips, badges, tables, cards).
4. Replace every hard-coded value with props or query data (field map in H.2–H.5). If a value has no backend source, follow H.1 (remove, make it real, or label it demo).
5. Delete Stitch "state preview" toggles ("Empty State / Shimmer / Gateway Error", "Simulate state", "Live Sample / Validation Error"). Real states come from the query status. Keep a **dev-only** `/__states` gallery route (behind `import.meta.env.DEV`) that renders every `StateBlock` for review.
6. Check at 1440 px and at **360 / 390 px** before marking the screen done. The Stitch mobile pages overflow the right edge at 390 px (seen in review), so fix with `min-w-0`, wrapping and `overflow-x-auto` tables.

---

### H.1 Content honesty pass (mandatory, applies to every screen)

The Stitch output contains claims PARAKH does not make, or cannot prove yet. Found by grep across the 31 `code.html` files:

| Found in the designs | Files | Action |
|---|---|---|
| "ISO 27001 Certified" footer | 10 | **Remove.** Not certified |
| "CCTNS / I4C / 1930 Live Integration", "Sync 1930 Blacklist", "CCTNS feed", "NCRP gateway timeout" | 9 + | **Remove or reword** to what exists: "Import / export adapters (sample formats)" (G.4). Error screens become a generic "Server unreachable" |
| NPCI mule-registry / NPCI lien / "NPCI verified" checks | 16 | **Remove.** No NPCI access. Show only "matches N verified PARAKH cases" (real query) |
| "Decompiling Smali bytecode", "Androguard v4.1", "dynamic emulation", "Docker sandbox", "Hardware FIDO2 token" | 4 + | **Reword** to the true method: "Static analysis: manifest, signatures, DEX strings. The app is never installed or run." |
| Voice "Acoustic AI / synthetic spectral probe / deepfake" | 2 | **Remove.** Voice = transcription (Gemini, optional) then the same text analysis |
| "TRAI DLT whitelist verified", "DLT Entity ID", "DoT Sanchar Saathi match" | 2 + | **Remove** as verification claims. May stay as *advice* ("check the sender header") and as links to official portals |
| "Message verified as legitimate & safe", "Download Safe / Verification Certificate", "Verified by Rajasthan Police Cyber Cell", "Sovereign certified by I4C" | 2 + 2 + 1 | **Remove.** An automated tool cannot certify safety, and a "safe certificate" creates liability. LOW verdict wording stays exactly: **"No strong scam signs found — still verify."** `parakh_verification_verdict_clean_safe` is **dropped** as a separate screen (merged into the LOW variant) |
| Invented figures: "82% chance of freezing", "94.2% funds freeze success", "₹4.8 Cr lien frozen", "142 scams neutralised today", "1,890+ APKs flagged", "1,284 cases", "+18.4% velocity", "engine latency 412 ms", "98.4% confidence" | 4 + many | **Bind to live API values** (dashboard and heat-list stats from the DB) or **remove** (public success-rate claims). Never a hard-coded number |
| "Section 91 CrPC notice", "Batch Sec. 91 CrPC lien" | 10 | **→ BNSS 2023 §94** (production) / **§106** (seizure/freeze). CrPC was replaced on 1 Jul 2024 |
| "Section 65B certificate" | 9 | **→ BSA 2023 §63** |
| "Sec 420 IPC" | 1 | **→ BNS 2023 §318(4)** |
| Officer names and signatures ("Insp. Vikram Singh Rathore", "R. Meena IPS", "Insp. R. S. Shekhawat"), seal stamps, a realistic complainant mobile `+91 94140 22918` | 10 | **Replace** with the logged-in user's real profile (Phase C) or clearly fictional demo labels; **no signatures or seals** on generated documents; complainant data uses synthetic `+91 9XXXX XXXXX` patterns |
| Rajasthan Police emblem / state insignia on report and login | 2 | **Neutral placeholder** "Official emblem (to be added with authorisation)" |
| Hot-linked AI photos (`lh3.googleusercontent.com`), including "Physical deployments of the PARAKH Geo-Engine" (PHQ video wall, officers at terminals) | 7 | **Remove.** Shows deployments that don't exist, and needs internet. Use our own SVG illustrations or none |
| "33 districts / 33 Cyber Thanas" | several | **Don't hard-code.** Count from the units table / district GeoJSON. Verify Rajasthan's current official district count before the demo |
| Help / rescue phone numbers (district cyber cells, bank hotlines, discom 1912) | 3 | Move to `app/data/trusted_channels.py` / `official_directory.py`. **Verify every number against the official website**, recording source and date. Unverified numbers are not shown |
| "Nearest cyber police station" Google map + named station-in-charge | 1 | Static list from verified data; no third-party map tiles (offline, privacy); no officer names |

Add `scripts/check_ui_claims.py`. It greps `frontend/src` for banned phrases (`ISO 27001`, `CrPC`, `65B`, `IPC`, `NPCI verified`, `Smali`, `deepfake`, `certificate of safety`, `lh3.googleusercontent`, `cdn.tailwindcss`, `fonts.googleapis`) and fails CI if any appear.

---

### H.2 Citizen core screens (demo-critical; build first after H.0)

Responsive rule: **one route per page**. The desktop Stitch screen gives the ≥ 768 px layout and the matching mobile screen gives the < 768 px layout, in the same component. Mobile screens are not separate pages.

| Route | Stitch source (desktop · mobile) | Backend (exists ✓ / new ✚) | Key bindings and notes |
|---|---|---|---|
| `/` Home | `parakh_citizen_cyber_safety_portal` · `parakh_citizen_mobile_home` · hero motion spec `parakh_hero_map_animation_storyboard_4_frame_sequence` | ✓ `POST /parakh/analyze` (quick check) | Hero map per storyboard (H.7). "Active threat patterns in Rajasthan" cards come from `scam_rules` typology packs (B.3), served by ✚ `GET /parakh/typologies` (or a static JSON generated from the rule file at build). Drop the "Today in Rajasthan: N scams neutralised" and "Safety metrics ₹ Cr" blocks unless backed by ✚ `GET /parakh/public-stats` (aggregate counts only, no case data; off by default) |
| `/check` | `parakh_check_something_suspicious_forensic_multi_modal_triage` · `parakh_citizen_mobile_check` + `citizen_app_check_something_suspicious_mobile` (merge the two mobile versions) | ✓ `/parakh/analyze`, `/parakh/url/analyze`, `/parakh/email/analyze`, `/parakh/media/extract`, `/parakh/qr/analyze`; ✚ `POST /parakh/identifier/check` | Modes: Message · Link · Email · Screenshot · Voice · QR · App · **UPI ID** · **Phone** (the mobile designs add UPI and Phone; they need ✚ `identifier/check`, see H.6). Live chips via `lib/identifiers.js`. Consent checkbox **unchecked** for screenshot/voice. "Paste sample scam" buttons use demo samples from `eval/demo_cases.json` |
| `/check` (processing) | `parakh_analysing_message` | — | Stages drive from real request lifecycle (sent → response → render). No invented "comparing 240+ templates" counters; show the real rule-pack size from ✚ `GET /parakh/meta` (rule count, version) if wanted |
| `/result` | HIGH/MEDIUM: `parakh_verification_result_high_risk_scam_alert` · `citizen_app_scan_fraud_risk_verdict` / `parakh_citizen_mobile_result_verdict` (merge). LOW: `parakh_verification_result_low_risk_clean_notice`. States: `parakh_verification_result_empty_loading_error_states` | ✓ `AnalysisResponse` / `UrlAnalysis` / `EmailAnalysisResponse`; ✓ `/parakh/explain-simply`, `/parakh/safe-next-step`, `/parakh/report-to-police` | Gauge = `confidence` / risk score; source tag = `analysis_source` (RULES / AI / AI+RULES, B.9); highlights = `red_flags[].phrase`; "Why we think so" = findings with weights (B.2); link sandbox = `url_analyses[]` (domain age only in officer mode or when RDAP is on); "Common doubts" = `safe-next-step`; "Explain simply" EN/हिं/Hinglish = `explain-simply`; "Send to police review queue" = `report-to-police` with **consent + district** (C.3). Remove "Download safe certificate". The result is kept in memory only (ADR-001); "Download PDF" = client-side print of the result |
| `/apk` | `parakh_app_check_apk_forensic_scanner` · `parakh_citizen_mobile_app_check`; states `parakh_apk_upload_empty_loading_error_states` | ✓ `POST /parakh/apk/analyze` (`CitizenApkAnalysis`) | Identity card ← `details.package / app_label / version / sha256 / certificate`; "Signing: v2 ✓ v3 ✓" ← B.7 `signing_schemes`; triangulation ← COMBO findings; permission groups ← `details.permission_profile`; "Hidden inside the app" ← identifiers (IP, URL, UPI, TELEGRAM_BOT masked, FIREBASE); "Already seen in police cases" ← `reported_identifiers`. Remove "Paste APK direct URL" (fetching APKs from URLs is not built; add later behind the website-fetch guard if wanted). Error state copy: "Not a valid APK / archive unsafe" from `ApkParsingError`, no "escalate to Special Cyber PS" button for citizens |
| `/check` QR result | `parakh_qr_code_forensic_risk_verdict` | ✓ `POST /parakh/qr/analyze`; ✚ `identifier/check` for "similar QR reports" | Payload decoded **in the browser** (`lib/qr.js`); image never uploaded. URL QR reads `url_analysis.registered_domain` (D11). "Similar QR reports (Rajasthan)" panel only shows real counts from verified cases; otherwise hidden |

---

### H.3 Citizen support screens

| Route | Stitch source | Backend | Notes |
|---|---|---|---|
| `/rescue` | `parakh_cyber_victim_rescue_emergency_sop` · `parakh_citizen_mobile_rescue` | ✓ `POST /parakh/rescue-plan` | 6 exposure cards → `exposure_state`; checklist phases from the playbook; district cyber-cell list from verified `trusted_channels`; "Package evidence on device" → evidence locker. Remove "82% chance" and "94.2% success rate" |
| `/help` | `parakh_official_help_directory_organisation_verifier` | ✓ `/parakh/organisation/verify`, `/parakh/trusted-channels` | Verifier result card = real `OrganisationVerifyResponse`; directory cards from data files with verified numbers only; keep the "No legal provision for digital arrest" directive card (true and useful) |
| `/learn` | `parakh_scam_explorer_cyber_defence_academy` | static JSON | 12 scam types + quiz from `frontend/src/content/scams.{en,hi}.json`, aligned with B.3 categories; drop AI photo posters (or replace with our own downloadable PDF guides later) |
| `/evidence` | **no Stitch design** (nav links to it) | none (on-device) | Generate in Stitch (H.5 prompt list) or build from kit: list + add + redacted export; port `vault.js` |
| `/status/:ref` | **no Stitch design** | ✚ `GET /parakh/report-status/{ref}` (status only: received / assigned / notices sent; no case data) | Problem 11 from research; optional P1 |
| `/privacy` | **no design** ("Read security whitepaper" link) | static | Plain page: what is stored and when (ADR-001), DPDP note |
| `*` 404 / offline | **no design** | — | Simple kit page |

---

### H.4 Officer core screens

| Route | Stitch source | Backend (✓ exists / ✚ new / Phase) | Key bindings and notes |
|---|---|---|---|
| `/investigate/login` | `parakh_officer_login_law_enforcement_authentication` | ✓ `/investigate/auth/login`; ✚ TOTP step (C.4) | Step 1 label "Username / PNO", step 2 "Authenticator code" (TOTP), **not** "OTP to CUG SIM" unless SMS OTP is built. Lockout banner from API error. Remove "Hardware FIDO2" text |
| `/investigate` dashboard | `parakh_officer_dashboard_command_centre_1` (use this; `_2` is a near-duplicate, keep only as reference) | ✚ `GET /investigate/dashboard/summary` (KPIs, artifact mix, 30-day trend by risk, cases by district) · ✚ `GET /investigate/activity` (from `audit_events`, C.5) · ✓ `GET /investigate/cases` | KPIs, choropleth, donut, trend and activity feed **all from the API**, scoped to the user's unit. "Batch Section 91 CrPC notice" → "Generate action packs" (D.4). "Re-assign to …" → C.3 assign. Case table states from `parakh_case_table_empty_loading_error_states` |
| `/investigate/cases` | same table (full page) | ✓ `GET /investigate/cases`, CSV exports | Filters: type, risk, status, source, district, date; bulk select → export / action pack |
| `/investigate/submit` | `parakh_new_forensic_analysis_evidence_ingestion` | ✓ `/investigate/submit`, `/apk/analyze`, `/website/analyze`; ✚ C.1 case fields | Fields: NCRP ack, FIR no., police station, offence act, amount lost, victim count, victim district, note. "Recent ingestions" = `GET /investigate/cases?created_by=me&limit=5` (✚ filter). Remove "Docker isolated sandbox / quota 142/250". Website tab says "fetched without JavaScript through a protected route" (true, B.8) |
| `/investigate/case/:id` | `parakh_case_detail_forensic_dossier_prk_20261118_k7p2qx` | ✓ case detail, `/linked`, `/similar`, report, JSON; ✚ assign/transfer (C.3), evidence (E), audit timeline (C.5), action pack button (D.4) | The design is APK-centric. Build **per-artifact sections**: APK (insights panel), WEBSITE (fetch details, kit fingerprint, page QR), URL (domain age, redirect chain), EMAIL (SPF/DKIM/DMARC), MESSAGE (highlighted text). "Cryptographic chain of custody" block ← `evidence_items` (E.1). Status stepper ← `CaseStatus`. Investigation remark tags `[Internal note] [FSL forward] [Court]` → note categories (✚ small field). Identifier panel shows **role** chips (B.6) |
| `/investigate/campaigns` | `parakh_campaign_intelligence_syndicate_network_graph`; states `parakh_campaign_graph_empty_loading_error_states` | ✓ `GET /investigate/campaigns`; ✚ loss/victims (G.1) | Network graph from `nodes`/`edges`; campaign list from `campaigns[]`; "How the campaign evolved" from `timeline[]` with real word diffs; "Merge clusters" removed (campaigns are computed, not hand-merged), or kept as officer annotation in a later phase. "Physics" toggle → layout on/off |
| `/investigate/heatlist` | `parakh_heat_list_hot_identifiers_registry`; states `parakh_heat_list_empty_loading_error_states` | ✓ `GET /investigate/heatlist`; ✚ velocity %, verification tier (C.4), first-seen district (G.3) | Podium = top 3; registry table = entries; "Verified vs citizen" toggle (C.4 quarantine). Remove "Sync 1930 blacklist / SFTP queue / manual SFTP". "Export sanction list" → identifiers CSV |
| `/investigate/identifier/:type/:value` | **no Stitch design** (sidebar has "Identifiers") | ✓ `GET /investigate/identifiers/{type}/cases` | Generate in Stitch (H.5 list); layout per wireframe #13 |
| Report (print) | `parakh_investigation_report_statutory_print_sec_63_bsa_2023` | ✓ `GET /investigate/cases/{id}/report` | **Restyle the server-side HTML** in `report_builder.py` (moving to Jinja2 in D.3) to this design, so printing/PDF stays server-side and tested. Generated by = logged-in officer; no signatures/seals; §63 section = draft certificate (D.3); remove the "57.1% recovery rate" and "Lien order" lines unless backed by data |

---

### H.5 Screens still missing from Stitch (generate them, then build)

These appear in the plan and wireframe but have **no Stitch design**. Generate each in the same Stitch project using the *Civic Vigilance Light* system: paste the DESIGN.md style anchor, then the wireframe description of the panel (wireframe #). Then build it with the kit.

| # | Screen | Route | Depends on phase | Wireframe ref |
|---|---|---|---|---|
| 1 | Identifier pivot | `/investigate/identifier/:type/:value` | existing API | #13 |
| 2 | Action pack | `/investigate/case/:id/action-pack` | D.2–D.4 | #17 |
| 3 | My queue (SHO / SP views) | `/investigate/queue` | D.5 | #18 |
| 4 | Document review and approval (A4 preview, versions, approval timeline, approve with TOTP / return with comment / dispatch) | `/investigate/documents/:id` | D.5 | #19 |
| 5 | Evidence and chargesheet readiness | `/investigate/case/:id/evidence` | E | #20 |
| 6 | MIS report | `/investigate/reports/mis` | D.7 | #21 |
| 7 | Money trail and freeze priority | `/investigate/money-trail` | G.2 (stretch) | #22 |
| 8 | Admin: units, users, roles, audit-chain verify | `/investigate/admin` | C | #23 |
| 9 | Accuracy and demo readiness (reads `eval/report.json`) | `/investigate/accuracy` | A | #24 |
| 10 | Citizen-report verification queue (quarantine) | `/investigate/verify-reports` | C.4 | — |
| 11 | Assign / transfer modal (§78 rule message) | modal on case detail | C.3 | #12 |
| 12 | Notifications drawer (overdue items, new links) | drawer in officer shell | C.5 / D.5 | — |
| 13 | Officer profile / sessions / TOTP enrolment | `/investigate/profile` | C.4 | — |
| 14 | Citizen evidence locker | `/evidence` | existing (on-device) | #8 |
| 15 | Citizen report status | `/status/:ref` | ✚ | — |
| 16 | 404 / offline page, privacy page | `*`, `/privacy` | — | — |

---

### H.6 Backend additions the designs require

| Need (screen) | Endpoint / change | Phase | Notes |
|---|---|---|---|
| UPI / Phone check modes (mobile check), "seen in N complaints" chips, QR "similar reports" | ✚ `POST /parakh/identifier/check` → `{type, value, verified_case_count, blacklisted, advice}` | new (with B.5/B.6) | Anonymous, rate-limited, **counts only from verified cases** (C.4 quarantine), no case details; same logic as `link_service.reported_matches` |
| Dashboard KPIs, artifact mix, 30-day trend, district choropleth | ✚ `GET /investigate/dashboard/summary?days=30` | new | Scoped by `unit_path`; district from the new `victim_district` field |
| Activity feed | ✚ `GET /investigate/activity?limit=20` | C.5 | Built from `audit_events` |
| Officer identity in shell (name, rank, PNO, unit) | extend `GET /investigate/me` | C.1 | |
| Case fields on submit/detail (FIR, NCRP, district, station, amount, victims, offence act) | extend `InvestigateSubmitRequest`, `CaseDetail` | C.1 | |
| "Recent ingestions" | `GET /investigate/cases?created_by=me` | small | |
| Heat-list velocity % and verification tier | extend `HeatListEntry` (`velocity_pct`, `verified_case_count`, `citizen_case_count`) | C.4 | Velocity = last 7 days vs previous 7 days |
| Campaign loss / victims | extend `Campaign` | G.1 | |
| Signing schemes, packer, components on APK screens | extend APK `details` | B.7 | |
| Signal-map weights on result | include per-finding `weight` in `AnalysisResponse.red_flags` (or a new `signals[]`) | B.2 | |
| Typology cards (home, learn) | ✚ `GET /parakh/typologies` or build-time JSON from `scam_rules.py` | B.3 | Keeps education in sync with detection |
| Rule-pack meta (version, rule count) | ✚ `GET /parakh/meta` | small | Replaces invented counters |
| Citizen report status | ✚ `GET /parakh/report-status/{ref}` | optional | |
| Report restyle | `report_builder.py` → Jinja2 template | D.3 | |
| SPA serving | `app/main.py` already serves `frontend/dist`; add a test that `/` returns the SPA and `/api/v1/health` still wins | H.8 | |

Every new endpoint gets a pytest and an OpenAPI schema. The frontend only calls endpoints listed here or in the existing API reference.

---

### H.7 Maps and motion

- **India outline:** use an **official Survey of India** boundary (the complete J&K and Ladakh as per the official map). Do not use generic world-atlas or community outlines that differ.
  - Rajasthan **district boundaries** from an official source (state GIS / data.gov.in). Record source, licence and date in `frontend/src/geo/SOURCES.md`.
  - Simplify with mapshaper to small TopoJSON files (target < 150 KB each), stored in `frontend/src/geo/`.
- **Hero animation** (`IndiaMap`) follows the Stitch storyboard: four frames over **3.2 s** with easing `cubic-bezier(0.16, 1, 0.3, 1)`:
  1. national baseline, opacity 0.35
  2. Rajasthan lifts (+12 px, sandstone fill, soft glow)
  3. pulse rings on district HQ nodes, arcs flowing in
  4. verdict cards appear

  After that a slow ambient loop runs (8–14 s). Under `prefers-reduced-motion`, show frame 4 static. Nodes and cards are **illustrative** (labelled as such), never "live telemetry".
- **Dashboard choropleth** (`RajasthanDistrictMap`): real district polygons coloured by **cases per victim district** from `dashboard/summary`, with a hover tooltip and click-to-filter the case table. This replaces the abstract hexagon shapes in the Stitch mock.
- **Campaign graph:** `d3-force` with a fixed random seed and 300 iterations computed once, so the layout is deterministic and the map doesn't reshuffle during a briefing. Under reduced motion, render the final positions directly.

---

### H.8 Testing, accessibility, build

- **Unit (Vitest + Testing Library):** kit components, `lib/identifiers.js` against the shared vectors file, i18n fallbacks, the `api.js` error mapping, and `vault.js` encrypt/decrypt round-trip.
- **E2E (Playwright, `frontend/e2e/`, rebuilt):**
  - citizen: message (EN + Hindi), link (`police.rajasthan.gov.in` → LOW), email `.eml`, QR (UPI payload), APK upload, screenshot consent gate, report-to-police with reference number
  - officer: login + TOTP, dashboard loads scoped data, case detail, campaign map, heat-list, report opens, cross-unit 404, three-role approval flow (D)
  - all run **offline** (network blocked except `localhost`)
- **Visual check:** Playwright screenshots of every route at 1440 and 390, compared by eye against the Stitch `screen.png`. Optional pixel diff on the kit gallery.
- **Accessibility:**
  - axe check in E2E, Lighthouse a11y ≥ 90 on citizen pages
  - every icon-only button has an `aria-label`; Hindi text in `lang="hi"` spans
  - risk is never conveyed by colour alone
- **CSP:** E2E asserts zero CSP violations in the console with the tightened policy (no Google or CDN domains).
- **Build and serve:**
  - `npm run build` → `frontend/dist`
  - FastAPI serves it (existing `app/main.py`)
  - `run.py` dev mode runs Vite on 5173 with the `/api` proxy
  - decide whether `dist` is committed (needed only for the Vercel citizen deploy; ADR-003) and update `.gitignore` and README accordingly
- **Performance:** citizen first load < 300 KB gzipped JS (officer code split out), fonts subset to Latin + Devanagari, maps lazy-loaded.

---

### H.9 Exit criteria

- [ ] H.0 scaffold builds; tokens, fonts and icons are self-hosted; **no CDN or Google URLs** in `frontend/dist` (`check_ui_claims.py` passes)
- [ ] All H.2 citizen routes work end-to-end against the real backend, offline, at 1440 and 390 px, with no horizontal overflow
- [ ] All H.4 officer routes work against the real backend; every number shown comes from an API response (spot-check list in `DEMO.md`)
- [ ] H.1 honesty table fully resolved: no CrPC / 65B / IPC references, no ISO / live-integration / NPCI / sandbox / deepfake claims, no safe certificates, no officer signatures or seals, no hot-linked images
- [ ] Every screen uses the `StateBlock` empty / loading / error states; the dev-only `/__states` gallery renders them all
- [ ] E2E suite green offline; axe shows no serious issues; zero CSP violations
- [ ] H.5 screens needed for the demo storyline (identifier pivot, action pack, queue, document review, evidence) are designed and built, or explicitly cut from the storyline in Phase I

---

## Phase I — Demo readiness, deck and jury (P0, last)

### I.1 Demo environment
- The demo laptop runs SQLite, `JOBS_MODE=inline`, Gemini **off** (rules only, proving the offline promise). Optionally turn it on for one "AI+RULES" moment.
- `python scripts/reset_demo_db.py && python scripts/demo_check.py --offline` gives all green before going on stage.
- Frontend: `cd frontend && npm run build`, then FastAPI serves `frontend/dist` on one port. Do not demo from the Vite dev server. Turn Wi-Fi off once and click through every route to prove there are no CDN or font requests (H.8).
- Demo the new UI at 1440 px for officer screens and in a phone-sized window (390 px) for one citizen check, to show the responsive design.
- Three browser profiles are logged in: IO, SHO, SP. A fourth window is the citizen app.
- A hotspot backup for the network; every demo step also works offline.
- Keep a printed failure table (extend `DEMO.md`).

### I.2 Demo storyline (about 7 minutes)
1. **Citizen (60 s):**
   - a Hindi KYC SMS → HIGH
   - `police.rajasthan.gov.in` → LOW (shows we fixed false positives)
   - the RTO-challan APK → "Do not install", with the accessibility service and Telegram bot found inside
   - "Report to police" with consent → a reference number
2. **Operator → IO (60 s):** the citizen report appears in the station queue. The SHO assigns it to an SI. The §78 rule blocks assigning an IT Act case to the SI and requires an Inspector (shown live).
3. **Intelligence (90 s):** linked cases → campaign map → the rotated phone number but the same UPI ID → heat-list → campaign total loss.
4. **Action pack (90 s):** the IO generates 5 drafts, then submits. The SHO approves 3 and returns 1 with a comment. The SP approves the freeze (TOTP prompt), which is shown red because it's overdue.
5. **Evidence (45 s):** the bundle zip, the manifest hashes, the §63 draft, the checklist "7/9 ready", and "Audit chain verified ✓".
6. **Proof (30 s):** the `eval/report.md` slide with precision and recall on the golden set, plus the load-test numbers.

### I.3 Deck changes (to `PARAKH_PS01_Hackathon_Deck.pptx`)
| Slide | Content |
|---|---|
| "What police actually struggle with" | 4–5 sourced problems (recovery rate, charge-sheet rate, FSL backlog, vacancies, bank-delay court order), each with its source |
| "Detection is not the bottleneck. Action is." | Manual flow vs PARAKH flow, with the **measured** time from the station visit |
| "One case, one click, five notices" | Before/after table |
| "Built for the chain of command" | Org chart + "Jurisdiction-scoped", "§78 enforced", "Audit chain" badges |
| "Measured, not claimed" | Golden-set size, precision/recall per category, 0 official false positives, load-test p95 |
| Roadmap | Move roles and audit logging to "Delivered" |

Fix the number drift: tests, rules and categories on slides must be generated from the code (`scripts/project_stats.py`).

### I.4 Jury Q&A preparation (extend DEMO.md)
- Are documents legally valid? (Drafts, reviewed by the officer, templates to be vetted by the legal cell.)
- Do you replace CCTNS / NCRP / I4C systems? (No: a station-level working layer with import/export adapters.)
- How accurate are you? (The golden-set numbers, and how the set was built.)
- What about privacy and sovereignty? (Offline-first, AI optional and off, no data leaves the server by default.)
- What happens with officer transfers? (Access is tied to the unit; cases are reassigned; history is kept.)
- What can't it do? (No dynamic APK sandbox, no live bank/NCRP APIs without approval, JS-heavy sites need the optional renderer.)

---

## Appendix 1 — Study list and references

### Legal and policy (read the bare acts on [India Code](https://www.indiacode.nic.in/))
- Bharatiya Nagarik Suraksha Sanhita 2023: §94 (production of documents), §106 (seizure)
- Bharatiya Sakshya Adhiniyam 2023: §63 (electronic records certificate)
- Information Technology Act 2000: §78 (investigating rank), §79(3)(b) (intermediary takedown)
- Digital Personal Data Protection Act 2023 (citizen data handling)
- RBI draft framework on holding the disputed amount in suspected fraud ([News on AIR, Sept 2026](https://newsonair.gov.in/rbi-proposes-framework-to-freeze-only-disputed-transaction-amount-in-suspected-cyber-fraud-cases/))
- MP High Court on real-time coordination between police, banks and telecom ([SCC Online, July 2026](https://www.scconline.com/blog/post/2026/07/18/real-time-information-exchange-mechanism-needed-in-cyber-crimes-mp-hc/))

### Detection and parsing
- Unicode TR39 confusables / skeleton: https://www.unicode.org/reports/tr39/
- indic-transliteration: https://github.com/indic-transliteration/indic_transliteration_py
- libphonenumber / python-phonenumbers: https://github.com/google/libphonenumber, https://github.com/daviddrysdale/python-phonenumbers
- tldextract (public suffix list): https://github.com/john-kurkowski/tldextract
- dnstwist (typosquatting ideas): https://github.com/elceef/dnstwist
- BIP-173 bech32 / BIP-350 bech32m: https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki, https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki
- TRON address format: https://developers.tron.network/docs/account
- Telegram Bot API (token format): https://core.telegram.org/bots/api
- RDAP JSON responses (RFC 9083): https://datatracker.ietf.org/doc/html/rfc9083
- APK Signature Scheme v2/v3: https://source.android.com/docs/security/features/apksigning/v2
- DEX format: https://source.android.com/docs/core/runtime/dex-format
- K7 Labs, SpyMax fake wedding invitation: https://labs.k7computing.com/index.php/spymax-a-fake-wedding-invitation-app-targeting-indian-mobile-users/
- CERT-In e-challan APK alert (coverage): https://www.freepressjournal.in/mumbai/cert-in-issues-alert-on-apk-malware-fraud-used-by-cybercriminals-to-steal-financial-data-via-fake-e-challan-bill-alerts
- Phishing-kit clustering by JavaScript behaviour (arXiv 2509.13186): https://arxiv.org/html/2509.13186v1
- Favicon-hash hunting (SANS ISC): https://isc.sans.edu/diary.html?date=2021-04-19
- zxing-cpp (QR decoding): https://pypi.org/project/zxing-cpp/
- Tesseract OCR + Hindi traineddata: https://github.com/tesseract-ocr/tesseract, https://github.com/tesseract-ocr/tessdata

### Datasets (check each licence before use)
- razorpay/ifsc (IFSC → bank, branch, district): https://github.com/razorpay/ifsc
- Spam SMS in Hindi (IEEE DataPort): https://ieee-dataport.org/documents/spam-sms-hindi-language
- Hinglish scam text (Hugging Face; small, partly synthetic): https://huggingface.co/bolewara/hinglish-scam-text-dataset
- SMS phishing systematic review, lists datasets including "RevisedIndian" (arXiv 2604.11429): https://arxiv.org/pdf/2604.11429
- MalwareBazaar (malicious APK samples; handle safely): https://bazaar.abuse.ch/
- URLhaus / OpenPhish (phishing URL feeds for testing): https://urlhaus.abuse.ch/, https://openphish.com/

### Similarity, graphs and scale
- Charikar (2002), *Similarity estimation techniques from rounding algorithms* (SimHash)
- Manku, Jain & Das Sarma (2007), *Detecting near-duplicates for web crawling* (SimHash at scale; shows why banding suits small Hamming thresholds)
- Broder (1997), *On the resemblance and containment of documents* (MinHash)
- Leskovec, Rajaraman & Ullman, *Mining of Massive Datasets*, ch. 3 (LSH banding): http://www.mmds.org/
- datasketch (MinHash LSH): https://github.com/ekzhu/datasketch
- PostgreSQL pg_trgm: https://www.postgresql.org/docs/current/pgtrgm.html
- networkx Louvain communities: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html
- Anderson, Shumailov & Ahmed (2018), *Making Bitcoin Legal* (FIFO / Clayton's Case taint tracing)
- arq (async job queue): https://arq-docs.helpmanual.io/ · Locust (load testing): https://locust.io/

### Security and evidence
- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- RFC 6238 TOTP: https://datatracker.ietf.org/doc/html/rfc6238 · pyotp: https://github.com/pyauth/pyotp
- RFC 3161 timestamps: https://datatracker.ietf.org/doc/html/rfc3161
- WARC (ISO 28500) / warcio: https://iipc.github.io/warc-specifications/, https://github.com/webrecorder/warcio
- STIX 2.1: https://oasis-open.github.io/cti-documentation/

### Problem context (for slides; verify against the primary source before quoting)
- India Justice Report 2025 (vacancies, training, forensic vacancies): https://indiajusticereport.org/files/National%20Factsheet%20IJR%204_English.pdf
- Status of Policing in India Report 2019 (working hours): https://www.lokniti.org/app/webroot/media/upload_files/SPIR%202019.pdf
- NCRB cyber crime disposal (charge-sheet / pendency): https://dataful.in/datasets/22401
- Rajasthan 2025 cyber fraud figures: https://the420.in/?p=119668

### People to talk to (most valuable study)
- One SHO or IO at a district cyber police station: notice formats, the time they take, the approval chain, pain points
- The hackathon organisers: the R4C dataset and evaluation expectations
- A bank nodal officer contact, if available: which request fields they need to respond fast

---

## Appendix 2 — New files and folders

```text
PARAKH/
├── planversionalpha.md                ← this file
├── eval/
│   ├── golden/{messages,urls,identifiers}.jsonl, apks/manifest.json, websites/*.html
│   ├── demo_cases.json
│   └── report.md / report.json        ← generated by scripts/evaluate.py
├── scripts/
│   ├── evaluate.py · fit_rule_weights.py · demo_check.py · reset_demo_db.py
│   ├── project_stats.py · rebuild_campaigns.py · generate_synthetic_cases.py
├── docs/
│   ├── legal_notes.md · loadtest.md
├── evidence_store/                    ← gitignored, write-once originals
├── loadtest/locustfile.py
├── alembic/                           ← Phase F
├── app/
│   ├── utils/text_normalise.py
│   ├── core/permissions.py
│   ├── data/
│   │   ├── protected_brands.py · addressees.py · approval_policy.py
│   │   ├── reference_icons.json · ifsc_banks.json (subset)
│   │   └── rules/  (optional split of scam_rules.py by typology)
│   ├── services/
│   │   ├── identifier_roles.py · audit_service.py · addressee_resolver.py
│   │   ├── document_service.py · workflow_service.py · mis_service.py
│   │   ├── evidence_store.py · money_trail.py · geo_intel.py
│   ├── api/documents.py
│   ├── templates/documents/*.html.j2
│   ├── integrations/ncrp_import.py · export_cctns.py · export_stix.py
│   └── workers/                       ← Phase F (arq)
├── tests/
│   ├── test_text_normalise.py · test_eval_gate.py · test_permissions_scoping.py
│   ├── test_audit_chain.py · test_workflow.py · test_action_pack.py
│   ├── test_evidence_bundle.py · test_money_trail.py · test_lsh.py
├── design/stitch/                     ← Stitch export moved here (reference only; .zip gitignored)
└── frontend/                          ← rebuilt in Phase H
    ├── index.html · package.json · vite.config.js · playwright.config.js
    ├── e2e/                           ← citizen + officer flows, run offline
    └── src/
        ├── main.jsx                   ← fonts, icons, tokens, QueryClient, router
        ├── app/  router.jsx · CitizenLayout.jsx · OfficerLayout.jsx · AuthContext.jsx
        ├── design/
        │   ├── tokens.css             ← Tailwind v4 @theme from DESIGN.md
        │   └── ui/  Button · IdentifierChip · RiskBadge · RiskCard · RiskGauge · SignalMap
        │            Stepper · Timeline · DataTable · KpiCard · Sparkline · Donut · AreaTrend
        │            StateBlock · Segmented · Tabs · Modal · Drawer · Toast · ConsentCheckbox
        │            FileDrop · NetworkGraph · IndiaMap · RajasthanDistrictMap
        ├── features/
        │   ├── citizen/  home · check · result · apk · qr · rescue · help · learn · evidence · status
        │   └── officer/  login · dashboard · cases · submit · case-detail · campaigns · heatlist
        │                 identifier · action-pack · queue · document · evidence · mis
        │                 money-trail · admin · accuracy · verify-reports · profile
        ├── lib/  api.js · queries/ · i18n.jsx · identifiers.js · vault.js · qr.js · redaction.js · format.js
        ├── content/  scams.en.json · scams.hi.json · en.json · hi.json
        ├── geo/  india.topo.json · rajasthan-districts.topo.json · SOURCES.md
        └── dev/  StatesGallery.jsx   ← /__states, dev builds only
```

Also new: `scripts/check_ui_claims.py` (H.1 banned-phrase gate), `tests/fixtures/identifier_vectors.json` (shared by pytest and Vitest).

---

## Appendix 3 — New dependencies

| Package | Phase | Why | Weight / risk |
|---|---|---|---|
| `phonenumbers` | B | International and landline extraction, carrier lookup | Pure Python, ~10 MB data |
| `indic-transliteration` | B | Devanagari → Latin matching view | Pure Python, small; optional |
| `zxing-cpp` | B | QR decoding on website images | Prebuilt wheels; optional, degrades to a limitation |
| `pytesseract` + Tesseract binary | B | Offline OCR for screenshots | External binary; optional |
| `jinja2` | D | Document templates (autoescape) | Small |
| `pyotp` | C | TOTP MFA | Pure Python, tiny |
| `warcio` | E | WARC capture | Small; optional |
| `playwright` (Python) | E | Screenshot capture in a worker | Heavy; optional, off by default |
| `asyncpg`, `alembic` | F | Postgres + migrations | Standard |
| `arq` (+ Redis) | F | Background jobs | Optional; `JOBS_MODE=inline` fallback |
| `networkx` | F/G | Louvain suggestion, graph utilities | Pure Python; optional |
| `scikit-learn` | B (dev only) | Fitting rule weights offline | **Dev-time only**, never a runtime dependency |
| `locust` | F (dev only) | Load testing | Dev-time only |

**Not needed (decided while writing this plan):** `androguard` (`pyaxmlparser` already parses v2/v3 signatures and the manifest XML), `imagehash` (our own dHash stays), `numpy` at runtime.

### Frontend (Phase H)

| Package | Why | Notes |
|---|---|---|
| `react`, `react-dom`, `react-router-dom`, `vite`, `tailwindcss` + `@tailwindcss/vite`, `framer-motion` | Existing stack (kept in `package.json`) | Reinstall: `node_modules` was removed |
| `@tanstack/react-query` | Uniform loading / empty / error states and caching for every API call | Small |
| `@fontsource-variable/plus-jakarta-sans`, `@fontsource/noto-sans-devanagari`, `@fontsource-variable/jetbrains-mono` | **Self-hosted fonts** for offline demo and strict CSP | Replace Google Fonts links |
| `material-symbols` | Self-hosted Material Symbols Outlined (icons used by every Stitch screen) | Replaces `lucide-react` |
| `d3-geo`, `topojson-client` | India / Rajasthan maps from official boundaries | Tree-shaken; maps lazy-loaded |
| `d3-force` | Deterministic campaign network layout | Fixed seed and iterations |
| `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom` (dev) | Component and unit tests | |
| `@playwright/test` (dev) | E2E, offline runs, screenshots | Browsers already cached locally |

**Not used:** the Tailwind CDN script, Google Fonts or Material Symbols CDN links, `lh3.googleusercontent.com` images, chart libraries (our own SVG charts are lighter and match the design).

---

*Plan version alpha. Update the status checkboxes as work lands, and record any decision that changes this plan in DECISIONS.md as a new ADR.*
