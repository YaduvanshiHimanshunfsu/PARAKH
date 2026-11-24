# Contributing to PARAKH

Thank you for looking at this. PARAKH is a police tool, so a few of our rules
are stricter than a typical project's. They exist because a wrong claim on
screen, or an unexplainable verdict, has consequences in a real case file.

## The three rules that matter most

### 1. Never claim what the system cannot do

`scripts/check_ui_claims.py` runs in CI and fails the build if the interface
claims a certification, an integration or a capability we do not have. If a
feature is a placeholder, it must say so on screen.

```bash
python scripts/check_ui_claims.py
```

If you need to add a phrase the gate blocks, the right fix is almost always to
change the claim, not the gate.

### 2. Every verdict must be explainable

A score with no reason behind it cannot go in a case diary. Any new detection
logic must return:

- which rule fired (`rule_id`),
- the exact phrase in the user's own text that matched,
- how much it contributed.

### 3. Accuracy changes are measured, not asserted

Tune on the **dev** split only. The test split exists to tell you the truth.

```bash
python scripts/fit_rule_weights.py        # inspect the fit
python scripts/fit_rule_weights.py --write # commit new weights
python scripts/evaluate.py                 # regenerate eval/report.md
```

Commit the weights and the regenerated report together, and quote the
before/after numbers in the pull-request description.

## Getting set up

```bash
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cd frontend && npm install && cd ..
python scripts/reset_demo_db.py --yes
```

## Before you open a pull request

```bash
python -m pytest -q                  # backend
python scripts/check_ui_claims.py    # honesty gate
python scripts/evaluate.py           # accuracy, if you touched detection
cd frontend && npx vitest run && npm run build && npx playwright test
```

## Writing rules

New detection rules live in `app/data/scam_rules.py`. Each needs:

- a stable `rule_id`, a `source` naming where the pattern came from, and a weight;
- **English, Hinglish and Devanagari variants** — Hindi is not an afterthought here;
- at least three positive tests (one per language) and two hard negatives in
  `tests/test_rule_engine_v2.py`.

> **The Devanagari trap.** Python's `\b` is defined over `\w`, and Hindi vowel
> signs (matras) are combining marks that `str.isalnum()` rejects — so `\b`
> matches *inside* Hindi words. A pattern like `\bन\s+करें` silently matches
> "स्कैन करें" ("scan it"), which once turned an awareness guard into a
> scam-suppressor. Use explicit lookarounds instead.
> `tests/test_rule_patterns.py` fails on any `\b` adjacent to Devanagari.

## Style

- Comments explain **why**, not what. Assume the reader can read the code.
- Prefer a clear name over a comment that explains a bad one.
- Match the surrounding file. The codebase builds HTML with escaped f-strings
  rather than a template engine; follow that rather than adding a dependency.
- New runtime dependencies need a reason in the pull request. We have turned
  several down because they were heavy for one function.

## Data and privacy

- **Never commit a case database, a real complaint, or anything with a real
  person's details.** `*.db` is gitignored for this reason.
- The golden dataset is synthetic, modelled on public advisory patterns. Keep
  it that way unless a data-sharing agreement says otherwise.
- Do not add a real nodal-officer contact to `app/data/addressees.py`. Sample
  entries are labelled as samples on purpose.

## Reporting a security issue

See [SECURITY.md](SECURITY.md). Please do not open a public issue for a
vulnerability.
