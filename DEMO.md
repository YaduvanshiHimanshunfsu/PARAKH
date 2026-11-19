# Demo Runbook â€” Rajasthan Police PS01

A five-minute walkthrough that demonstrates every PS01 Must-Have. Rehearse it twice before judging.

---

## Before you start (10 minutes)

```powershell
# 1. Clear any stale Gemini key from the OS environment.
#    An invalid key costs ~1.1s of dead retries on EVERY analysis, and OS
#    environment variables override .env.
$env:GEMINI_API_KEY = ""
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "User")

# 2. Set a real officer password in .env (not the template value).

# 3. Build the frontend.
cd frontend; npm run build; cd ..

# 4. Seed blacklist + a cross-linked demo campaign.
python -m app.db.seed
python -m app.db.demo_seed --reset

# 5. Start the app.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Pre-flight check** â€” open `http://127.0.0.1:8000/api/v1/health`. All of these must be true:

```json
{ "status": "ok", "investigation_store_ready": true, "case_count": 14,
  "apk_analysis_available": true, "website_analysis_available": true }
```

Keep one tab on the citizen app (`/`) and one on the console (`/investigate`).

---

## The narrative

The demo follows **one fraud campaign** across three artifact types. Everything is seeded to
converge on three identifiers:

| Identifier | Appears in |
|---|---|
| `richplan@ybl` | SMS Ã— 2, website, Android app |
| `+919812345670` | SMS Ã— 3, website, Android app |
| `45.133.1.9` | SMS, Android app |

That convergence *is* the pitch â€” PS01's background section complains that these threats
"reuse the same domains, app identifiers, phone numbers and payment accounts, yet they are
reported and examined separately."

---

## Walkthrough (5 minutes)

### 1 Â· Citizen side â€” prevention (45s)

Open `/check`. Paste:

```
RichPlan Investment: Guaranteed 10% daily returns! Referral bonus on every
downline member. Joining package Rs 5000. Pay richplan@ybl or call 9812345670
```

**Say:** verdict, confidence, and the exact phrases that triggered it â€” in seconds, in Hindi too.

**Then say:** "Nothing was stored. Citizen analysis is ephemeral by design." *(ADR-001)*

### 2 Â· Officer console â€” case history and search (45s)

Open `/investigate`, sign in. Point at the 14 seeded cases across messages, apps and websites.

Search `richplan@ybl`. **Four cases** come back â€” an SMS, another SMS, a website, and an
Android app.

**Say:** "One search across every artifact type. This is the fragmentation the problem
statement describes, solved."

### 3 Â· APK analysis â€” the differentiator (90s)

Open the **QuickCash Loan** case.

Point at the permission findings, especially `COMBO_LOAN_APP_HARVESTING`:

> *"The app can read SMS, copy the phonebook, and send both to a server. This is the defining
> permission signature of a predatory instant-loan app: OTP interception plus contact
> harvesting for harassment-based recovery."*

**Say:** "Any single permission is unremarkable. The combination is the fraud signature â€” and
every finding cites the reviewed rule behind it, so the risk score is explainable, not a
black box."

Then scroll to extracted identifiers: the C2 IP, the UPI ID, the Telegram channel â€” all pulled
out of the APK's compiled code.

**Say:** "Static only. The app was never installed or executed."

### 4 Â· Linking â€” one campaign (60s)

Still on the APK case, point at **Linked cases**: three cases at link strength 27, sharing
phone + Telegram + UPI.

Click through to the website case. Show the Ponzi content indicators â€” guaranteed returns,
referral chain, joining package â€” and the payment identifiers scraped off the page.

**Say:** "An Android app and a website, connected by the account the money goes to."

### 5 Â· Repeat content and heat-list (45s)

Open either RichPlan SMS â†’ **Repeat content** shows the other at 100%, `EXACT_TEMPLATE`.

**Say:** "Same template, different amounts. Detected as one campaign, not two reports."

Open **Heat-list**: `+919812345670` at the top with 5 cases.

**Say:** "The most-reported identifiers, ranked. This is where an investigation starts."

### 6 Â· Report (45s)

Back on any case â†’ **Full report**. Show case ID, every indicator with its reasoning, the
identifier table, linked cases, and the evidence snapshot.

Then click **Redacted** â€” identifiers masked for sharing outside the investigation.

**Say:** "Full copy for the case file, redacted copy for anything shared. Print to PDF from
the browser, or export JSON and CSV."

---

## Closing line

> "One platform. Messages, Android apps and websites analysed with explainable indicators,
> actionable identifiers extracted from each, and everything linked into a single searchable
> case history â€” built on a privacy-first citizen tool that still stores nothing unless
> someone explicitly chooses to report."

---

## If something breaks

| Symptom | Cause | Fix |
|---|---|---|
| Every analysis takes ~1s longer | Invalid `GEMINI_API_KEY` in OS env | Clear it. The rule engine handles everything in this demo; no key is needed. |
| Dashboard is empty | Demo data not seeded | `python -m app.db.demo_seed --reset` |
| Login fails | `OFFICER_USERNAME`/`OFFICER_PASSWORD` unset at startup | Set both in `.env`, restart. The account is created on boot. |
| `investigation_store_ready: false` | Database file not writable | Check the working directory; delete `PARAKH_cases.db` and re-seed. |
| Website analysis fails | Target unreachable, or guard refused it | Expected for private/unreachable addresses. Use the seeded website cases instead. |
| APK upload rejected | Not a real APK, or over 60 MB | Validation is strict by design. Use the seeded APK cases. |

**Never demo live against a real fraud site.** Use the seeded cases; they are deterministic and
always available.

---

## Questions judges are likely to ask

**"Does this work without the AI?"**
Yes â€” and that is deliberate. APK and website analysis are fully deterministic rule engines, and
messages fall back to 27 reviewed regex rules. Everything in this demo runs with no API key.

**"How do you avoid false accusations?"**
Nothing is labelled fraudulent on a single weak signal. Verdicts are Low/Medium/High with the
specific triggering indicators listed, and every report states that indicators are evidence for
investigation, not proof of criminal conduct.

**"What about privacy?"**
Citizen analysis stores nothing â€” enforced by a test that fails the build if a citizen request
ever writes a row. Crossing into the police queue requires explicit consent.

**"Is the APK analysis safe to run?"**
It is static. Magic bytes are checked, zip-bomb ratios rejected, and the file is inspected in
memory. It is never installed, executed, or unpacked anywhere a loader could reach.

**"What can't it do?"**
No dynamic sandboxing, no takedown, no access to private accounts â€” all explicitly out of PS01
scope. Packed APKs and JavaScript-rendered sites yield less, and the tool says so rather than
reporting a clean result. See the Known Limitations table in the README.

