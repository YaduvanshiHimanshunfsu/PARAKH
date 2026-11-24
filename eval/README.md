# Golden dataset and evaluation (Phase A)

`scripts/evaluate.py` measures detection accuracy offline. The rule engine runs with no AI key and no network. `tests/test_eval_gate.py` fails CI if any protected metric falls below `baseline.json`.

| File | Items | Content |
|---|---|---|
| `golden/messages_scam.jsonl` | 145 | Scam (133) and suspicious (12) SMS/WhatsApp text: English, Hindi (Devanagari), Hinglish |
| `golden/messages_safe.jsonl` | 155 | Legitimate messages, many of them hard negatives: genuine bank alerts, real OTP messages, police/RBI advisories that mention "digital arrest" or "OTP", real discom bills |
| `golden/urls.jsonl` | 120 | 60 official or legitimate sites (incl. brand-substring traps like `firstpost.com`, `sbicard.com`) and 60 look-alike, typosquat, shortener, IP-host and scheme URLs |
| `golden/identifiers.jsonl` | 80 | Text with the identifiers that **should** be extracted, including Phase B targets (TRON, Telegram `@handle`, bot token, international and landline numbers, IMEI), plus 20 negatives |
| `golden/websites.jsonl` | 30 | Saved page HTML: 15 fraudulent (Ponzi, betting, loan, task, phishing), 15 legitimate |
| `golden/apks.json` | 20 | APK specifications built at run time with `tests/apk_fixtures.py` (10 malicious, 10 benign, incl. a real SMS app and a dialer as hard negatives) |
| `demo_cases.json` | 16 | Exact stage inputs for `scripts/demo_check.py` (live server check) |

## Where the data comes from

All items are **team-written synthetic examples** modelled on public advisory patterns: Rajasthan Police and other state police advisories, CERT-In alerts, and RBI and I4C awareness messages. They contain **no real victim data**. The phone numbers, UPI IDs and domains are demo values.

Crypto addresses and IMEIs that are meant to be valid were generated with correct checksums. One deliberately broken TRON address is included as a negative case.

Before quoting numbers outside the team, add real samples:
- the organisers' R4C dataset
- anonymised cyber-cell samples
- licensed public sets listed in `planversionalpha.md` A.1
- real APKs: benign ones pulled from Play Store installs with `adb pull`; malicious ones from MalwareBazaar, kept only in a password-protected archive and never installed

## Split

The split is deterministic: an item is in `test` when `sha256(id)[0] % 10 < 3`, which gives about 30%. Tune rules on `dev` and quote only `test` numbers.

## Commands

```text
python scripts/evaluate.py                    # writes eval/report.md and eval/report.json
python scripts/evaluate.py --write-baseline   # after an intentional improvement
python scripts/demo_check.py                  # against a running server (all cases)
python scripts/demo_check.py --skip-phase-b   # only cases expected to pass today
```
