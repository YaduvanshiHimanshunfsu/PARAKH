# Wireframe generation prompt — PARAKH

A single, self-contained prompt for a wireframing tool (Google Stitch, Figma AI,
v0, Uizard, Claude/GPT with an HTML canvas, or a human designer). It describes
every screen in the shipped route table, so the output matches the real product
rather than an imagined one.

**How to use it:** paste everything between the horizontal rules below. If the
tool limits prompt length, paste §1–§5 first (they set the system up), then feed
§6 one screen group at a time.

---

## PROMPT BEGINS

You are producing **low-to-mid fidelity wireframes** for a working civic-tech
product called **PARAKH**. Wireframes only: grey boxes, real labels, real
hierarchy. No photography, no gradients, no illustration, no invented branding.
Use the one accent colour only where the spec says a risk or status signal
belongs.

### 1. What the product is

PARAKH is a cyber-fraud triage and investigation system built for the Rajasthan
Police. It has **two completely separate faces** that must not look alike:

- **A citizen face** (public, unauthenticated, mobile-first). A member of the
  public pastes a suspicious message, link, email, screenshot, voice note, QR
  code or UPI ID and gets a plain-language verdict plus what to do next.
- **An officer console** (authenticated, desktop-first). A police officer works
  a case, extracts the forensic identifiers, and generates the legal
  requisitions the case needs — which then travel up a real chain of command
  for approval.

The product's core thesis, which the wireframes must make visible:
**detecting the fraud is the easy half; producing the paperwork and getting it
approved is where the time actually goes.** The officer screens should feel
like a workflow tool, not a dashboard of charts.

### 2. Audience and hard constraints

- **Bilingual, English + Hindi (Devanagari), everywhere.** Every label needs
  room for a Hindi string roughly 1.3× the English width. Devanagari sits
  taller than Latin — give line-height headroom. Show the language toggle in
  the citizen header as a two-state segmented control: `English | हिन्दी`.
- **Low-end Android, one hand, poor network.** Citizen screens are designed at
  **390 px** first. Primary actions sit in the lower half of the screen.
- **Officers work on 1280–1440 px Windows desktops**, often at 125 % OS
  scaling. Assume less vertical room than you think.
- **Accessibility is not optional.** Minimum 16 px body text, 44 px touch
  targets, visible focus rings, and **no information carried by colour alone**
  (see the tri-signal rule in §3).

### 3. Design system — "Civic Vigilance Light"

Light theme only. Calm, institutional, document-like. Closer to a government
form than to a consumer app.

**Type**
| Role | Family |
|---|---|
| UI + body | Plus Jakarta Sans |
| Hindi | Noto Sans Devanagari |
| Identifiers, references, code | JetBrains Mono |

**Surfaces and text**
| Token | Hex | Use |
|---|---|---|
| canvas | `#F7F8FB` | page background |
| sand | `#FBF7F1` | warm section band |
| card | `#FFFFFF` | elevated card |
| line | `#E2E8F0` | 1 px perimeter |
| ink | `#0F172A` | primary text |
| ink-2 | `#475569` | secondary text |
| ink-3 | `#64748B` | muted / captions |

**Brand**
| Token | Hex | Use |
|---|---|---|
| primary | `#1D4ED8` | primary police action |
| accent | `#E07A2F` | sandstone/saffron: fills, icons, borders |
| accent-strong | `#C2410C` | accent *buttons* (the lighter accent fails AA with white text) |

**The risk tri-signal — the most important rule in this system.**
Risk is *always* communicated by three things at once: a background tint, a
darkened ink colour for the text, and a distinct icon/shape. Never by hue alone.

| Band | Tint | Text ink | Icon |
|---|---|---|---|
| HIGH / SCAM | `#FEF2F2` | `#B91C1C` | filled octagon / `dangerous` |
| MEDIUM / SUSPICIOUS | `#FFFBEB` | `#B45309` | triangle / `warning` |
| LOW / SAFE | `#ECFDF5` | `#047857` | circle-check / `verified` |

**Forensic identifier palette.** In the officer console every extracted
identifier gets a monospace chip with a type-coloured left border or dot:
UPI `#7C3AED`, phone `#2563EB`, bank account `#B45309`, IFSC `#A16207`,
domain `#0D9488`, URL `#475569`, email `#0891B2`, Telegram `#0284C7`,
IP `#E11D48`, crypto wallet `#EA580C`, app package `#4F46E5`,
signing certificate `#6D28D9`.

**Shape and depth**: 8–12 px radii on cards, 999 px on chips. Depth comes from
a 1 px border plus a very soft shadow — not from heavy elevation.

### 4. Global layout

**Citizen shell**
- Header: a thin saffron helpline strip (national cyber helpline **1930**),
  then wordmark "PARAKH" + tagline, desktop nav, language toggle, and a
  secondary "Officer login" link pushed to the far right.
- Desktop nav: Home · Check · APK · Rescue · Help · Learn · Evidence · Status.
- Mobile: a 5-item bottom tab bar (Home, Check, Rescue, Help, Status); the rest
  moves into the Help screen.
- Footer: a privacy link and an explicit line stating what is and is not stored.

**Officer shell**
- Persistent **left sidebar, 260 px**, collapsing to an overlay drawer below
  1024 px. Sidebar header = wordmark + "Investigation console". Section label
  "Operational modules", then: Dashboard · Cases · Approval queue ·
  New submission · Campaigns · Heat-list.
- Sidebar footer: officer display name, and **below it in small caps their
  role** (e.g. `IO`, `STATION_HEAD`, `SUPERVISOR`, `STATE_VIEWER`).
- Top bar: a global identifier search (typing a UPI ID or phone number shows a
  "UPI detected" type chip inside the field), and a primary
  **+ New submission** button.

**Breakpoints to deliver**: 390 px (citizen primary), 768 px, 1440 px (officer
primary).

### 5. Component inventory

Draw these once as a small component sheet, then reuse them:

1. **Verdict banner** — tri-signal tint, verdict word, confidence, category.
2. **Risk chip** — small tri-signal pill.
3. **Identifier chip** — monospace, type-coloured, with a copy affordance.
4. **Evidence/red-flag row** — the exact quoted phrase on the left in a quote
   style, the plain-language reason on the right.
5. **Action-step list** — numbered, imperative, max 5 items.
6. **Case row** — reference, category, risk chip, assigned officer, age, SLA.
7. **Document card** — document name, statute, status pill, SLA countdown, and
   the action buttons permitted at its current stage.
8. **Chain-of-command trail** — a horizontal stepper of who did what, when.
9. **Approval stepper node** — a rank-badged circle with name, action and a
   state tag.
10. **Empty / loading / error / offline** states for every data region.
11. **Segmented control** (used for both the language toggle and the 7 check
    modes).
12. **Audit status line** — a one-line "Audit chain verified (N events)"
    indicator with a tri-signal dot.

### 6. Screens

Draw all of the following. The path is the real route; keep it visible as a
small caption so the wireframes can be matched to the build.

#### 6A. Citizen — public

**1. Home — `/`**
Hero: one sentence on what PARAKH does, a large single input with placeholder
"Paste the message or link you received", and a prominent **Check now**
button. Below, a row of six secondary entry cards (Screenshot, Voice note, QR
code, APK file, UPI/Phone, Email). Then a "Just lost money?" band in accent
tint linking to Rescue, with **1930** shown at display size. Then a strip of
three very short "how it works" steps. Footer explains that nothing is stored
without the user asking.

**2. Check — `/check?mode=…`**
A **7-mode segmented control** across the top, labelled "What do you want to
check?":
`Message / संदेश` · `Link / लिंक` · `Email / ईमेल` ·
`Screenshot / स्क्रीनशॉट` · `Voice note / वॉइस` · `QR code / क्यूआर` ·
`UPI / Phone`.
Draw a variant for each mode:
- **Message**: large textarea, a language selector (Auto-detect / English /
  Hindi), character counter, submit.
- **Link**: single URL field, plus a warning that the page will be fetched
  server-side and never opened in the user's browser.
- **Email**: a paste area for full raw headers, with a hint about where to find
  "Show original".
- **Screenshot / Voice note**: a drop zone with file-type and size limits, a
  selected-file row with a remove control, and an explicit note that media is
  analysed and discarded.
- **QR code**: image drop zone; after decode, show the **decoded destination as
  text before anything else**, because the whole point is to not scan it.
- **UPI / Phone**: a single identifier field with a live-detected type chip.
Right rail (desktop only): a short "what we never ask for" reassurance card.
Include the **submitting** state with a determinate progress affordance.

**3. Result — `/result`**
The most important citizen screen. Top to bottom:
1. **Verdict banner** (tri-signal): the verdict word, a confidence figure, the
   scam category in human words, and severity. Categories come from a fixed
   vocabulary of 19 named types plus UNKNOWN — e.g. Digital arrest, UPI fraud,
   KYC scam, OTP theft, Loan-app fraud, Sextortion, Malicious app.
2. **A one-line Hindi summary**, always present, in Devanagari.
3. **"Why we think so"** — the evidence rows. Each quotes the *exact* phrase
   from the user's own text and explains it. This section must look like
   evidence, not like marketing.
4. **Psychological tactics used** — small chips (urgency, authority, secrecy,
   fear, reward).
5. **What to do now** — a numbered action list, the first item largest.
6. **Link/URL findings**, when present: the resolved domain, its age, whether
   it is a look-alike of a real brand, and which real brand it imitates.
7. **A disclosure line naming the analysis source** — AI, AI+RULES, or
   RULE_FALLBACK — so the user always knows whether a live model or the offline
   rule engine produced this.
8. Footer actions: **Report to police** (primary), Share safely, Check another.
Draw three variants of this screen: HIGH/SCAM, MEDIUM/SUSPICIOUS, LOW/SAFE.
Also draw the **degraded state**, where the AI provider is unavailable and the
rule engine answered — it must be labelled, not hidden.

**4. APK check — `/apk`**
An APK drop zone, then a static-analysis report: package name, app label,
requested permissions grouped by sensitivity (with SMS / accessibility /
install-packages flagged in the HIGH tri-signal), signing-certificate details,
icon look-alike comparison against real bank and government apps, and a final
verdict banner. Explicitly state that the app is never executed.

**5. Rescue — `/rescue`**
A time-critical screen for someone who has just lost money. A **golden-hour
countdown framing** at the top, then a hard-numbered checklist: call 1930, file
on cybercrime.gov.in, call the bank, freeze the account, preserve evidence.
Each step is a card with a phone/link action. No marketing copy at all.

**6. Help — `/help`**
Helpline directory and the full nav for mobile users: 1930, local cyber police
station lookup, bank fraud numbers, and a short FAQ accordion.

**7. Learn — `/learn`**
A grid of short scam-pattern explainer cards, filterable by category, each
with a real-looking example message and the giveaway highlighted.

**8. Evidence — `/evidence`**
Guidance on capturing and preserving evidence correctly, plus a bundle builder:
the user adds the items they have and gets a checklist to carry to the police
station.

**9. Status — `/status` and `/status/:reference`**
Two states on one route. Without a reference: a single lookup field for a
report reference. With one: a timeline of the report's progress through
registration, triage, assignment and action — shown as a vertical stepper with
dates, deliberately coarse so it reveals nothing operational.

**10. Privacy — `/privacy`**
A plain document page. Short paragraphs, a table of what is stored and for how
long, and a stated retention period.

**11. Not found — `*`**
Minimal, with a route back to Check.

#### 6B. Officer console — authenticated

**12. Login — `/investigate/login`**
A narrow centred card on the canvas colour. Username and password, an error
state, and — critically — a **lockout state** that says the account is
temporarily locked after repeated failures and shows the remaining wait. A
second step for **TOTP** (6-digit code) that appears only for accounts
requiring MFA. Below the card, a small, clearly-marked **demo accounts** panel
listing role logins, because this is a demonstrable system:
`sp.jaipur` (SP, Supervisor) · `dysp.cyber` (DySP, Supervisor) ·
`sho.cyber` (Inspector, Station head) · `io.si.sharma` (SI, IO) ·
`op.hc` (HC, Operator) · `io.btp` (Inspector, IO, Bharatpur) ·
`viewer.state` (ADG, read-only). Mark the panel plainly as demonstration-only.

**13. Dashboard — `/investigate`**
Not a chart wall. Top: four compact counters — open cases, awaiting my
approval, overdue against SLA, new citizen reports in the shared intake queue.
Then two columns: **"Needs me now"** (a list of documents awaiting this
officer's approval, each with an SLA countdown) and **"Recent activity"** (the
audit stream in plain sentences). A right rail shows the officer's **scope**:
which unit they see and whether that is station, district, range or state —
and the audit-chain verified line.

**14. Cases — `/investigate/cases`**
A dense table: reference, received, category, risk chip, amount, assigned
officer, unit, SLA state. Filters across the top (risk, category, unit,
assignment, overdue only). Draw the **empty state** and a **row-selected**
state. Include a visible banner stating that the list is **scoped to the
officer's unit subtree**, so an officer is never shown cases outside their
command.

**15. Approval queue — `/investigate/queue`**
The chain-of-command screen. A list of **document cards** awaiting action by
this officer, grouped by stage (Station approval / District approval). Each
card: document name, statute, the case it belongs to, the addressee, who
submitted it and when, an SLA countdown that turns to the HIGH tri-signal when
overdue, and the permitted actions — **Approve**, **Send back**, **Edit**.
Show an **overdue** card and an **empty** state.
Include a **refusal state**: when the officer who drafted a document opens it,
the approve action is replaced by an explanation that separation of duties
prevents approving one's own draft.

**16. New submission — `/investigate/submit`**
An officer-side intake form: the suspicious content, the complainant's details,
amount lost, channel, and attachments. Submits into the case store.

**17. Case detail — `/investigate/case/:caseId`** — the densest screen; draw it
most carefully. Suggested three-region layout:
- **Header**: case reference, category, risk chip, amount, received date,
  assigned officer, unit, status.
- **Left / main column**, as stacked sections:
  1. **The reported content**, verbatim, in a quoted block.
  2. **Analysis** — verdict, evidence rows, tactics.
  3. **Extracted identifiers** — the identifier chips, each with a **role
     label**: `SUSPECT`, `VICTIM`, `IMPERSONATED BRAND`, `OFFICIAL CONTACT`,
     `UNKNOWN`. Make the distinction visually loud; only SUSPECT and UNKNOWN
     identifiers link cases together, and a victim's own number must visibly
     never be actionable.
  4. **Linked cases** — other cases sharing an identifier, with the shared
     identifier named.
  5. **Action pack** — see the panel below.
  6. **Chain of custody / audit trail** — an append-only list of events with
     actor, action, timestamp, and a verified-hash indicator.
- **Right rail — Case command panel**: Assign to officer, Transfer unit, Verify
  audit chain, Close case. Include the **refusal state** for an IT Act offence
  assigned below Inspector rank: the action is blocked and the reason is stated
  on screen, citing section 78 of the Information Technology Act, 2000.

**18. Action pack panel** (inside case detail; draw as its own sheet too)
Two phases.
- **Plan**: "PARAKH can draft N documents for this case." A list of proposed
  documents, each showing the resolved **addressee** and a confidence state —
  **Confirmed**, **Verify before sending**, or **Unresolved** — because the
  bank or provider is inferred from the identifier and the officer must be told
  how certain that inference is. A **Generate drafts** button.
- **Generated**: a document card per draft. The document vocabulary is fixed:
  | Document | Statute | SLA |
  |---|---|---|
  | Request to hold disputed funds | BNSS 2023, s.106 | 2 h |
  | Notice to produce documents (bank) | BNSS 2023, s.94 | 24 h |
  | Notice to produce subscriber and call records | BNSS 2023, s.94 | 24 h |
  | Fraud number report (Sanchar Saathi / Chakshu) | DoT channel | 24 h |
  | Request to suspend a domain and disclose registrant | IT Act 2000, s.79(3)(b) | 24 h |
  | Notice to a hosting provider | IT Act 2000, s.79(3)(b) | 24 h |
  | Intermediary takedown and disclosure notice | IT Act 2000, s.79(3)(b) | 24 h |
  | Certificate for electronic evidence (Part A) | BSA 2023, s.63 | 48 h |
  Each card carries a status pill through the lifecycle: **Draft → Submitted →
  Station approved → District approved → Dispatched → Response recorded →
  Closed**, with **Sent back** and **Cancelled** as branches. Show the actions
  available at each status, and a **chain-of-command trail** under the card.

**19. Document preview** (a modal or a dedicated panel)
Render a draft as a document on a page. It must visibly show a diagonal
**DRAFT** watermark and an **empty signature block** — PARAKH never renders a
signature, a seal or an officer's name as a signatory. Actions: Edit, Submit
for approval, Download.

**20. Campaigns — `/investigate/campaigns`**
Clusters of related cases presented as campaign cards: the shared identifiers
or template that binds them, case count, total amount, first and last seen,
and the units affected. One expanded campaign shows its member cases.

**21. Heat-list — `/investigate/heatlist`**
A ranked table of the most active suspect identifiers: the identifier chip, its
type, how many cases it appears in, total amount, first and last seen, and
whether any document has already been sent about it. Each row links to the
identifier pivot.

**22. Identifier pivot — `/investigate/identifier/:type/:value`**
Everything known about one identifier. Header: the identifier in monospace at
display size, its type, its validity (checksum-verified or not), and its role.
Then: every case it appears in, every document ever raised about it, and a
timeline of its appearances.

### 7. States to include

For every data region, wireframe: **loading** (skeleton), **empty** (with the
reason and the next action), **error** (with a retry), and where relevant
**offline / degraded** (the rule engine answered instead of the AI).
Also wireframe at least one **permission-refused** state per console screen —
this product's distinguishing behaviour is that it *states why it refused*
rather than hiding the control.

### 8. Honesty rules the wireframes must respect

These are product constraints, not styling preferences. Do not violate them
even if they make a screen less impressive:

1. Never draw a signature, a seal, a letterhead crest or a signatory name on a
   generated document.
2. Never show a fabricated statistic, success rate, "cases solved" counter or
   testimonial. Where a number is shown, it must be a count of real rows.
3. Never imply the system reports to or acts on behalf of a bank, a telecom
   operator or a government portal. It drafts requests for a human to send.
4. Always label whether a verdict came from the AI or the offline rule engine.
5. Never present an identifier as actionable without showing its role.

### 9. Deliverable

For each screen: the stated breakpoint(s), annotated regions, and real label
text in English with the Hindi string shown for the citizen screens. Produce a
component sheet first (§5), then the citizen flow (§6A), then the officer
console (§6B). Keep the two faces visually distinct: the citizen side is
spacious, warm and single-column; the console is dense, cool and
multi-column.

## PROMPT ENDS

---

## Shorter variant

If a tool caps the prompt length, this condensed version still produces a
usable result:

> Wireframe a bilingual (English + Hindi) two-face civic-tech product called
> PARAKH, for the Rajasthan Police. Light theme, institutional, document-like:
> canvas `#F7F8FB`, ink `#0F172A`, primary `#1D4ED8`, accent `#E07A2F`. Risk is
> always shown as tint + darkened ink + distinct icon, never colour alone
> (high `#FEF2F2`/`#B91C1C`, medium `#FFFBEB`/`#B45309`, low
> `#ECFDF5`/`#047857`).
>
> **Face 1 — citizen, mobile-first at 390 px, unauthenticated:** Home with one
> paste-and-check input; a Check screen with a 7-mode segmented control
> (message, link, email, screenshot, voice note, QR code, UPI/phone); a Result
> screen whose hierarchy is verdict banner → one-line Hindi summary → evidence
> rows quoting the user's own words → psychological tactics → numbered next
> steps → a line naming whether the AI or the offline rule engine answered;
> an APK static-analysis report; a golden-hour Rescue checklist built around
> helpline 1930; Help, Learn, Evidence, Status lookup and Privacy pages.
>
> **Face 2 — officer console, desktop-first at 1440 px, authenticated,** with a
> 260 px left sidebar: Login (with lockout and TOTP states and a
> demonstration-only role-account panel); a Dashboard of "needs me now" rather
> than charts; a unit-scoped Cases table; an **Approval queue** of legal
> documents awaiting this officer's approval with SLA countdowns; a dense Case
> detail screen with the reported content, the analysis, extracted forensic
> identifier chips each carrying a role (suspect / victim / impersonated brand
> / official contact), linked cases, an **action pack** that drafts eight fixed
> document types under BNSS 2023 s.94 and s.106, IT Act 2000 s.79(3)(b) and
> BSA 2023 s.63, and an append-only audit trail; plus Campaigns, a Heat-list of
> active suspect identifiers, and an identifier pivot page.
>
> Draw loading, empty, error and **permission-refused** states throughout — the
> console's signature behaviour is stating why it refused an action. Generated
> documents must show a DRAFT watermark and an empty signature block; never
> draw a signature, a seal, or any fabricated statistic.
