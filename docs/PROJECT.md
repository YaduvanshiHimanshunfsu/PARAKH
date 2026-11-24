# PARAKH — Project Documentation

**Team Gravity** · Rajasthan Police Hackathon 2026 · Problem Statement PS01

> Written for a technical reviewer or an officer evaluating the system. For a
> quick overview, read the [README](../README.md) first.

---

## Contents

1. [The problem](#1-the-problem)
2. [What we built](#2-what-we-built)
3. [How it works](#3-how-it-works)
4. [Workflow, end to end](#4-workflow-end-to-end)
5. [Feature reference](#5-feature-reference)
6. [Technology choices and why](#6-technology-choices-and-why)
7. [What makes this different](#7-what-makes-this-different)
8. [Measured results](#8-measured-results)
9. [What we deliberately did not build](#9-what-we-deliberately-did-not-build)
10. [Conclusion](#10-conclusion)

---

## 1. The problem

### 1.1 The scale

Cyber financial fraud in India is no longer a niche crime. The National Cyber
Crime Reporting Portal receives lakhs of complaints a year, and Rajasthan's
Mewat belt is one of the country's recognised fraud origin clusters. The
pattern that repeats in nearly every case is the same:

1. A citizen receives a message — a KYC warning, an electricity disconnection
   notice, a "digital arrest" call, an e-challan with an `.apk` attached.
2. They cannot tell whether it is genuine. Nothing available to them answers
   *"is this real?"* in their own language, in seconds, without an account.
3. They lose money.
4. They report it — usually hours later, often after the money has already
   moved through three accounts.
5. At the police station, an officer begins typing the same five notices by
   hand that another officer typed yesterday for the same UPI ID.

### 1.2 The three gaps PS01 asks us to close

| Gap | What actually happens today |
|---|---|
| **Citizens cannot verify** | No trustworthy, instant, Hindi-first way to check a message, link, QR or app before acting on it. |
| **Police cannot see patterns** | Each complaint is a separate file. The same UPI ID in forty complaints across six districts looks like forty unrelated cases. |
| **Action is slow** | The "golden hour" for freezing money is spent drafting paperwork. Requisitions are retyped, approvals are chased on WhatsApp, and nothing records who approved what. |

### 1.3 Why existing tools do not close them

- **Spam filters** classify; they do not explain, and they do not help police.
- **Awareness campaigns** teach yesterday's scam. The lures change weekly.
- **Case-management software** records complaints; it does not analyse the
  content or draft the legal paperwork.
- **Generic AI chatbots** will answer "is this a scam?" — but they hallucinate,
  they need the internet, they cannot be audited, and no police force can put
  an unexplainable verdict in a case file.

---

## 2. What we built

PARAKH (परख — *to examine, to judge*) is one system with two faces over one
analysis engine and one case store.

### 2.1 Citizen mode — "is this real?"

Open, anonymous, no login, Hindi and English. A citizen can check a **message,
link, email, screenshot, voice note, QR code, UPI ID, phone number or Android
app**, and gets back:

- a plain-language verdict with the exact words that triggered it highlighted;
- *why*, in simple Hindi or English, suitable for reading aloud to a parent;
- what to do next, and what not to do;
- a rescue plan if they have already paid, with the 1930 golden-hour steps;
- the option — never the obligation — to send the item to police.

**Nothing is stored unless the citizen explicitly consents.** A check leaves no
trace: no account, no history, no identifier retained.

### 2.2 Investigation mode — "what is this connected to?"

Behind an officer login, the same analysis becomes a durable case:

- every UPI ID, phone number, domain, bank account, crypto wallet, Telegram
  handle and app signature is extracted and indexed;
- cases that share an identifier or near-identical text are **linked into
  campaigns**, with the text diffs between variants shown;
- a **heat-list** ranks identifiers by how many cases mention them, with the
  week-on-week trend;
- an **action pack** drafts the legal requisitions the case justifies;
- an **approval chain** routes each one through the real chain of command;
- every action is written to a **tamper-evident audit log**.

---

## 3. How it works

### 3.1 Architecture

```
┌────────────────────────────┐        ┌─────────────────────────────┐
│  Citizen app (React SPA)   │        │  Officer console (same SPA) │
│  no login · nothing stored │        │  login · jurisdiction-scoped│
└─────────────┬──────────────┘        └──────────────┬──────────────┘
              │          HTTPS / JSON                │
              └───────────────┬──────────────────────┘
                              ▼
                 ┌─────────────────────────┐
                 │   FastAPI (app/api)     │
                 │  rate limit · CSP · RBAC│
                 └───────────┬─────────────┘
                             ▼
   ┌─────────────────────────────────────────────────────────┐
   │                   Analysis engine                       │
   │  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌─────────┐ │
   │  │ Rule engine│ │ URL intel  │ │ APK static│ │ Website │ │
   │  │  (log-odds)│ │ (lookalike)│ │  parser   │ │ fetcher │ │
   │  └──────┬─────┘ └─────┬──────┘ └─────┬────┘ └────┬────┘ │
   │         └─────────────┴──────┬───────┴───────────┘      │
   │                 Identifier extractor (shared)           │
   │                              │                          │
   │              Optional AI (Gemini) ─── fused, never       │
   │                              │        trusted alone     │
   └──────────────────────────────┼──────────────────────────┘
                                  ▼
   ┌─────────────────────────────────────────────────────────┐
   │  Case store (SQLite → PostgreSQL)                       │
   │  cases · identifiers · findings · units · users         │
   │  documents · approvals · audit_events (hash chain)      │
   └─────────────────────────────────────────────────────────┘
```

### 3.2 The detection engine

The engine runs **offline by default**. The AI provider is optional, and when
it is present its answer is *fused* with the rules rather than replacing them.

**Step 1 — Normalise (anti-evasion).**
Scammers write `K.Y.C`, `KYC` with Cyrillic letters, `O​TP` with a zero-width
space, `0TP` with a digit. PARAKH builds a normalised *view* of the text —
Unicode NFKC, invisible-character removal, confusable folding, acronym
collapse, leet folding — while keeping an **index map back to the original**,
so a highlighted red flag is always an exact substring of what the citizen
actually pasted.

**Step 2 — Match reviewed rules.**
62 rules, each with English, Hinglish and Devanagari variants, covering digital
arrest, KYC/account-block lures, malicious APKs, task-job and Ponzi schemes,
loan-app harassment, betting, utility-bill scams, sextortion, marketplace
fraud and courier scams.

**Step 3 — Combine evidence as log-odds, not points.**

```
logit = bias + Σ wₖ · xₖ        p(scam) = 1 / (1 + e^(−logit))
```

Three rules keep the arithmetic honest:

- **Tactic de-duplication** — "urgent + immediately + today only" counts once.
- **Category cap** — at most two rules per fraud family contribute.
- **Guards** — negative-weight rules recognise *legitimate* structures: a real
  bank debit alert, an official "never share your OTP" advisory, a scheduled
  maintenance notice. A guard may reduce the evidence by at most 60% of it, so
  an awareness message scores SAFE while a scam that borrows advisory wording
  ("do not disconnect the call") does not escape.

Weights and both verdict thresholds are **fitted on a development split** by
`scripts/fit_rule_weights.py` (L2 logistic regression, plain gradient descent,
no runtime dependency) and committed as data. The held-out test split is never
used for tuning.

**Step 4 — Explain.** Every verdict returns the rules that fired, the exact
matched phrase and each rule's contribution. An officer can read *why*.

### 3.3 The URL and look-alike checker

- Whole-token brand matching against a reviewed protected-brand list, so
  `sbi-verify-kyc.in` is flagged while `firstpost.com` and `pineapple.com` are
  not (the old substring check flagged both).
- Typosquatting via **Optimal String Alignment distance** and a **confusable
  skeleton**, catching `hdfcbnak.com`, `sbii.co.in`, `jvvn1-bill.in` and
  `rnicrosoft.com`.
- `.gov.in` / `.nic.in` are trusted suffixes: a registered domain under them is
  never treated as brand-like.

### 3.4 The APK analyser

Static only — the file is read, never installed or executed.

- Signature schemes **v3 → v2 → v1**, so a modern package is not reported as
  unsigned.
- **Component-level manifest analysis**: a bound accessibility service, a
  notification listener, a device-admin receiver, a high-priority SMS receiver.
  This is how real banking trojans declare themselves; reading
  `<uses-permission>` alone missed every real sample.
- Accessibility + SMS interception together raise `BANKING_TROJAN_SIGNATURE`.
- The DEX string table is parsed properly (ULEB128 + MUTF-8), Base64 strings
  are decoded, and commercial packers are named as a stated limitation.

### 3.5 Identifier extraction and roles

Fourteen identifier types, each validated rather than merely shaped:

| Type | How precision is achieved |
|---|---|
| UPI, phone | libphonenumber validation; a mobile used as a UPI handle stays one UPI ID |
| Bitcoin, TRON | Base58Check / bech32 checksum verification |
| IMEI | Luhn check digit **plus** a nearby IMEI keyword |
| Telegram bot token | Stored as the bot id only; the token is masked and never used |
| Domain | Public Suffix List, so new abused TLDs work without a code change |

Every identifier also carries a **role** — `SUSPECT`, `VICTIM`,
`IMPERSONATED_BRAND`, `OFFICIAL_CONTACT`, `UNKNOWN`. Only `SUSPECT` and
`UNKNOWN` feed linking and the heat-list, so a victim's own number and a bank's
real helpline can never tie unrelated cases together.

---

## 4. Workflow, end to end

### 4.1 Citizen journey

```
Receives suspicious SMS
        │
        ▼
Opens PARAKH (no login) ──► pastes message ──► Analysis (<1s, offline)
        │                                              │
        │                                              ▼
        │                              Verdict + highlighted red flags
        │                              + plain Hindi explanation
        │                              + what to do / not do
        ▼
Already paid? ──► Rescue plan (1930, bank, evidence to keep)
        │
        ▼
Consents to report ──► lands in the police intake queue with a reference
```

### 4.2 Officer journey — the chain of command

This is the part most cyber-crime tools stop short of.

```
IO files or picks up a case
        │
        ▼
"Draft requisitions"  ──►  PARAKH groups the case's SUSPECT identifiers by
        │                   (document type, addressee) and drafts one notice
        │                   per group — not one per identifier
        ▼
 5 drafts, each unsigned, each watermarked DRAFT
        │
        ▼
IO submits the freeze request          ◄── SLA starts: 2 hours (golden hour)
        │
        ├─► IO tries to approve it     ──► REFUSED: the drafter may never
        │                                  approve their own document
        ▼
SHO (Inspector) approves at station level
        │
        ▼
SP (district) approves  ──► a freeze ALWAYS needs the district level
        │
        ▼
APPROVED ──► dispatch recorded (channel + reference)
        │
        ▼
Bank's reply recorded against the case
        │
        ▼
Everything above is in the tamper-evident audit chain
```

Assignment is checked against the law: **IT Act 2000 section 78** reserves
investigation of IT Act offences to an officer not below Inspector. Assigning
such a case to a Sub-Inspector is refused, and the refusal says why.

### 4.3 Jurisdiction

Units form a tree with a materialised path:

```
/RJ/
 ├── /RJ/JPR-RANGE/JPR-COMM/
 │     ├── /RJ/JPR-RANGE/JPR-COMM/JPR-CYBER-PS/
 │     └── /RJ/JPR-RANGE/JPR-COMM/JPR-SOUTH-PS/
 └── /RJ/BTP-RANGE/BTP-DISTRICT/BTP-CYBER-PS/
```

"Everything under my unit" is one indexed prefix query. An officer in
Bharatpur asking for a Jaipur case receives **404, not 403** — a 403 would
confirm the case exists, which is itself information about another district.

---

## 5. Feature reference

### 5.1 Citizen mode

| Feature | What it does |
|---|---|
| Message check | SMS, WhatsApp, chat text in English, Hindi or Hinglish |
| Link check | Look-alike domains, typosquats, risky TLDs, shorteners, HTTPS posture — the page is never opened |
| Email check | Pasted email or `.eml` upload, with SPF/DKIM/DMARC posture |
| Screenshot & voice | Text is read, shown for review, then checked; file is not stored |
| QR check | Decoded **on the device**; only the text is sent |
| UPI / phone check | Looks the identifier up in officer-verified cases and the reviewed blacklist |
| APK check | Permissions, signer, hidden endpoints, prior police matches |
| Rescue plan | Steps tailored to what the victim has already done |
| Evidence locker | AES-GCM encrypted, stays in the browser, exportable (full or redacted) |
| Report status | Track a submitted report by reference — stage only, never content |
| Learn | 12 scam types with red flags, plus a quiz that can ask the real analyser |

### 5.2 Investigation mode

| Feature | What it does |
|---|---|
| Command dashboard | KPIs, daily risk trend, artifact and risk mix, latest cases |
| Case register | Filter by text, type, risk, status, ownership; CSV export |
| Case dossier | Findings, identifiers with roles, highlighted evidence, linked and near-duplicate cases |
| Campaign map | Force-directed graph of cases ↔ shared identifiers, with variant timeline |
| Heat-list | Identifiers ranked by case count, with week-on-week trend |
| **Action pack** | Eight requisition types drafted from the case's identifiers |
| **Approval queue** | What is waiting for *this* officer, overdue first |
| **Chain of command** | Assign (with §78 check), transfer (reason mandatory), verify citizen reports |
| **Audit trail** | Hash-chained; the UI shows "Audit chain verified (N events)" |
| **MIS report** | Weekly figures for seniors, computed — never estimated |

### 5.3 The eight requisition types

| Document | Legal basis | Approval | SLA |
|---|---|---|---|
| Hold disputed funds | BNSS 2023 §106 | Station **+ district** | 2 h |
| Produce bank documents | BNSS 2023 §94 | Station (district above ₹10 L) | 24 h |
| Telecom CAF / CDR | BNSS 2023 §94 | Station | 24 h |
| Fraud number report | DoT Sanchar Saathi | Station | 24 h |
| Domain takedown | IT Act §79(3)(b) | Station + district | 24 h |
| Hosting abuse notice | IT Act §79(3)(b) | Station | 24 h |
| Intermediary takedown | IT Act §79(3)(b) | Station + district | 24 h |
| Electronic evidence certificate | BSA 2023 §63 | Station | 48 h |

---

## 6. Technology choices and why

| Layer | Choice | Why this, and not the obvious alternative |
|---|---|---|
| **API** | FastAPI + Pydantic v2 | Every response is schema-validated at the boundary. A malformed AI answer cannot reach the UI. Async suits the IO-bound analyser calls. |
| **Detection** | Reviewed rules + log-odds fusion | A police verdict must be explainable in a case file. "The model said so" is not evidence. Every rule has an id, a weight and a cited pattern source. |
| **AI** | Google Gemini, **optional** | The demo runs with it switched off. AI improves nuance; it is never the only path, and never overrides a strong rule hit. |
| **Storage** | SQLAlchemy async, SQLite → PostgreSQL | One connection-string change to scale. SQLite keeps the demo offline and dependency-free. |
| **APK parsing** | `pyaxmlparser` | Androguard is far heavier and slower, and nothing here needs full DEX disassembly. |
| **Phone numbers** | `libphonenumber` | Validates Indian landlines with STD codes and international formats; a regex could not, and produced false matches on order ids. |
| **Domains** | `tldextract` (embedded PSL) | New abused TLDs (`.cyou`, `.sbs`, `.bond`) work without editing a list. No hidden network call. |
| **Look-alikes** | OSA distance + TR39 skeleton | Inverts dnstwist: we test a *given* domain against protected brands, which is what an incoming URL needs. |
| **Frontend** | React 19 + Vite + Tailwind v4 | Fast cold start on a demo laptop; one SPA serves both faces with a lazily loaded officer bundle citizens never download. |
| **Charts** | Hand-built SVG | No chart library. Smaller, offline, and we control the accessibility (every chart ships a table view). |
| **Maps** | d3-geo + TopoJSON (Survey of India via DataMeet) | Attributed, offline boundary data; no tile-server dependency. |
| **Fonts & icons** | Self-hosted | The CSP is `font-src 'self'`. The demo must work with Wi-Fi switched off. |
| **QR decoding** | In-browser (BarcodeDetector → jsQR) | The image never leaves the device; only decoded text is sent. |
| **Audit** | SHA-256 hash chain | Makes a *partial* edit detectable, which is what an evidence trail needs. No blockchain: the cost buys nothing a chain does not. |
| **Tests** | pytest + Vitest + Playwright | 541 backend, 67 unit, 84 browser tests, including an assertion that no request leaves the local origin. |

---

## 7. What makes this different

Five things we have not seen combined elsewhere:

1. **One engine, two audiences.** The same analysis that tells a citizen "do
   not pay this" becomes the officer's linked, searchable case. The citizen's
   consented report *is* the intelligence feed.

2. **Explainability as a product requirement.** Every verdict names the rules
   that fired, their contribution and the matched phrase. A black-box score is
   useless in a case diary; ours can be read aloud in court.

3. **Hindi and Hinglish as first-class, not translated.** Rules carry native
   Devanagari and romanised variants. (A subtle trap we hit and fixed: Python's
   `\b` falls *inside* Hindi words because matras are not word characters —
   `tests/test_rule_patterns.py` now fails on any such pattern.)

4. **Detection connected to action.** Most tools stop at "this is a scam".
   PARAKH drafts the BNSS §94 notice, the §106 freeze request and the BSA §63
   certificate, groups identifiers so one provider gets one notice, routes it
   through the real approval chain, and records who approved what.

5. **Honesty built into the system.** `scripts/check_ui_claims.py` fails the
   build if the UI claims a certification we do not hold or an integration we
   do not have. Sample addressees are labelled as samples. Mappings that can
   change say "confirm before dispatch". Nothing invents a contact or a
   signature.

---

## 8. Measured results

Measured on a held-out test split (30% by hash of item id, never used for
tuning) of a 450-item golden dataset. Reproduce with
`python scripts/evaluate.py`; the report is committed at `eval/report.md`.

| Metric | Before Phase B | After | Target |
|---|---|---|---|
| SCAM precision | 0.75 | **1.00** | 0.92 ✅ |
| Risky recall | 0.625 | **0.979** | — |
| Hindi / Hinglish recall | 0.368 | **1.00** | 0.85 ✅ |
| Official-domain false positives | 9 | **0** | 0 ✅ |
| Identifier extraction F1 | 0.884 | **0.98** | 0.90 ✅ |
| APK detection accuracy | 1.00 | **1.00** | 0.90 ✅ |
| 3-class macro F1 | 0.37 | **0.649** | 0.85 ❌ |

The macro-F1 target is **not met**, and we state that plainly: the middle
`SUSPICIOUS` class is only 12 test items and is intrinsically fuzzy. SCAM and
SAFE, the two classes that drive real decisions, are both near-perfect.

**Test suite:** 541 backend tests, 67 frontend unit tests, 84 browser tests
across desktop (1440 px) and mobile (390 px).

---

## 9. What we deliberately did not build

Stating this matters as much as the feature list.

| Not built | Why |
|---|---|
| Live CCTNS / NCRP / bank API integration | Requires an MoU and credentials we do not have. PARAKH drafts the paperwork; dispatch is recorded manually. |
| Voice deepfake detection | We cannot validate it, so we do not claim it. |
| Automatic account freezing | A freeze is a legal act requiring an approved requisition — by design, never automatic. |
| Officer signatures or seals | Rendering one would forge authority. The block is left blank for the approving officer. |
| Nodal-officer contact directory | Not public. Entries are labelled samples for the officer to complete. |
| District choropleth on the dashboard | Needs a district field on each case and current LGD boundaries; shown as a labelled placeholder. |

---

## 10. Conclusion

PS01 asks for a system that helps citizens verify, helps police see patterns,
and makes action faster. PARAKH does all three, with every number in this
document reproducible by running the evaluation script, and every claim on
screen checked by a script that fails the build if it over-promises.

What we would most like a reviewer to notice is not the feature count. It is
that **the citizen's check and the officer's case file are the same artifact**.
A citizen in Bharatpur who checks a UPI ID is reading intelligence that an
officer in Jaipur generated; an officer in Jaipur opening a heat-list is
reading reports that citizens consented to send. That loop — verification
feeding investigation feeding verification — is the part that does not exist
today, and it is the part that gets cheaper the more it is used.

---

*PARAKH produces investigative indicators from automated analysis. Indicators
support an investigation; they are not proof of criminal conduct.*
