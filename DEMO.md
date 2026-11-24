# Demo Runbook — Rajasthan Police PS01

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
python -m app.db.demo_seed --export-apks samples   # APK files for the App check step

# 5. Start the app.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Pre-flight check** — open `http://127.0.0.1:8000/api/v1/health`. All of these must be true:

```json
{ "status": "ok", "investigation_store_ready": true, "case_count": 16,
  "apk_analysis_available": true, "website_analysis_available": true }
```

Keep one tab on the citizen app (`/`) and one on the console (`/investigate`).

---

## The narrative

The demo follows **one fraud campaign** across three artifact types. Everything is seeded to
converge on three identifiers:

| Identifier | Appears in |
|---|---|
| `richplan@ybl` | SMS × 2, website, Android app |
| `+919812345670` | SMS × 3, website, Android app |
| `45.133.1.9` | SMS, Android app |

That convergence *is* the pitch — PS01's background section complains that these threats
"reuse the same domains, app identifiers, phone numbers and payment accounts, yet they are
reported and examined separately."

---

## Walkthrough (5 minutes)

### 1 · Citizen side — prevention (45s)

Open `/check`. Paste:

```
RichPlan Investment: Guaranteed 10% daily returns! Referral bonus on every
downline member. Joining package Rs 5000. Pay richplan@ybl or call 9812345670
```

**Say:** verdict, confidence, and the exact phrases that triggered it — in seconds, in Hindi too.

**Then say:** "Nothing was stored. Citizen analysis is ephemeral by design." *(ADR-001)*

Click **App check** in the top menu and upload `samples/com.quickcash.instantloan.apk`.

**Say:** "A citizen got this loan app on WhatsApp. Before installing it: *High risk — do not
install*. Every permission in plain words — it reads your OTPs, copies your phonebook, draws
over your banking app. And *Already seen in police cases* — the citizen benefits from every
case the police have already analysed, without anything being stored."

### 2 · Officer console — case history and search (45s)

Open `/investigate`, sign in. Point at the 16 seeded cases across messages, apps and websites.

Search `richplan@ybl`. **Five cases** come back — three SMS, a website, and an Android app.

**Say:** "One search across every artifact type. This is the fragmentation the problem
statement describes, solved."

### 3 · APK analysis — the differentiator (90s)

Open the **QuickCash Loan** case.

Point at the permission findings, especially `COMBO_LOAN_APP_HARVESTING`:

> *"The app can read SMS, copy the phonebook, and send both to a server. This is the defining
> permission signature of a predatory instant-loan app: OTP interception plus contact
> harvesting for harassment-based recovery."*

**Say:** "Any single permission is unremarkable. The combination is the fraud signature — and
every finding cites the reviewed rule behind it, so the risk score is explainable, not a
black box."

Then scroll to extracted identifiers: the C2 IP, the UPI ID, the Telegram channel — all pulled
out of the APK's compiled code.

**Say:** "Static only. The app was never installed or executed."

### 4 · Linking — one campaign (60s)

Still on the APK case, point at **Linked cases** — SMS and the website, sharing phone,
Telegram and UPI. Then click **Campaign map**.

The RichPlan campaign is selected: six cases over three weeks, drawn as one cluster around
the UPI ID. Scroll to **How the campaign evolved**:

- 11 Nov — reworded copy: `10% → 12%`, `5000 → 9000`
- 20 Nov — `12% → 15%`, and the phone changes `9812345670 → 9123456780`

**Say:** "They changed the phone number. They did not change the account the money goes to —
so it is still one campaign."

Click the **Repeated template** campaign: two KYC messages with *no* shared identifier, linked
only by wording. **Say:** "New domain, same script. Still caught."

Click back into the RichPlan cluster and open the website node.

Click through to the website case. Show the Ponzi content indicators — guaranteed returns,
referral chain, joining package — and the payment identifiers scraped off the page.

**Say:** "An Android app and a website, connected by the account the money goes to."

### 5 · Repeat content and heat-list (45s)

Open either RichPlan SMS → **Repeat content** shows the other at 100%, `EXACT_TEMPLATE`.

**Say:** "Same template, different amounts. Detected as one campaign, not two reports."

Open **Heat-list**: `richplan@ybl` and `+919812345670` at the top with 5 cases each.

**Say:** "The most-reported identifiers, ranked. This is where an investigation starts."

### 6 · Report (45s)

Back on any case → **Full report**. Show case ID, every indicator with its reasoning, the
identifier table, linked cases, and the evidence snapshot.

Then click **Redacted** — identifiers masked for sharing outside the investigation.

**Say:** "Full copy for the case file, redacted copy for anything shared. Print to PDF from
the browser, or export JSON and CSV."

---

## Closing line

> "One platform. Messages, Android apps and websites analysed with explainable indicators,
> actionable identifiers extracted from each, and everything linked into a single searchable
> case history — built on a privacy-first citizen tool that still stores nothing unless
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
Yes — and that is deliberate. APK and website analysis are fully deterministic rule engines, and
messages fall back to 27 reviewed regex rules. Everything in this demo runs with no API key.

**"How do you avoid false accusations?"**
Nothing is labelled fraudulent on a single weak signal. Verdicts are Low/Medium/High with the
specific triggering indicators listed, and every report states that indicators are evidence for
investigation, not proof of criminal conduct.

**"What about privacy?"**
Citizen analysis stores nothing — enforced by a test that fails the build if a citizen request
ever writes a row. Crossing into the police queue requires explicit consent.

**"Is the APK analysis safe to run?"**
It is static. Magic bytes are checked, zip-bomb ratios rejected, and the file is inspected in
memory. It is never installed, executed, or unpacked anywhere a loader could reach.

**"What can't it do?"**
No dynamic sandboxing, no takedown, no access to private accounts — all explicitly out of PS01
scope. Packed APKs and JavaScript-rendered sites yield less, and the tool says so rather than
reporting a clean result. See the Known Limitations table in the README.

