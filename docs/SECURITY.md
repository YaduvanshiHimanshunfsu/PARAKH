# PARAKH — Security Model & Privacy Design

---

## Privacy Guarantee (ADR-001)

**Citizen Mode stores nothing.** This is not a configuration option — it is enforced structurally:

- `create_case()` is never called from any citizen route
- The automated test `test_citizen_mode_analysis_persists_nothing` asserts zero DB rows after a citizen analysis
- The only exception is `POST /parakh/report-to-police`, which requires **explicit user consent** (unchecked by default)

---

## Authentication

| Component | Mechanism |
|---|---|
| **Password hashing** | `hashlib.scrypt` (N=2¹⁶, r=8, p=1) — no native-wheel dependency |
| **Token generation** | `secrets.token_urlsafe(32)` |
| **Token storage** | Only `SHA-256(token)` stored in DB; raw token is never persisted |
| **Token expiry** | 12 hours (configurable via `AUTH_TOKEN_TTL_HOURS`) |
| **Session storage** | `sessionStorage` in browser — clears on tab close |
| **MFA** | Optional TOTP (`pyotp`) for Supervisor and Admin roles |

---

## SSRF Protection

All outbound HTTP requests (URL analysis, website fetch, redirect chains, RDAP) go through `_public_addresses()`.

**Blocked at every redirect hop (not just the first):**
- `127.0.0.0/8` — loopback
- `10.0.0.0/8` — RFC-1918
- `172.16.0.0/12` — RFC-1918
- `192.168.0.0/16` — RFC-1918
- `169.254.0.0/16` — link-local / AWS IMDS
- `::1` — IPv6 loopback
- `fc00::/7` — IPv6 ULA
- `fe80::/10` — IPv6 link-local

**Website fetch constraints:**
- 10s total timeout
- 2 MB stream cap (aborted mid-download on exceed)
- Maximum 3 redirects
- HTML/text content types only
- No JavaScript execution
- Generic browser User-Agent (not an operator fingerprint)

---

## Content Security

| Risk | Mitigation |
|---|---|
| **XSS in reports** | `html.escape()` on all user-supplied content in `report_builder.py` |
| **Script injection** | Verified by `test_ui_claims.py` — submitting `<script>alert(1)</script>` and asserting it cannot execute |
| **APK execution** | Static analysis only — APKs are never executed |
| **SQLi** | SQLAlchemy ORM — no raw SQL interpolation |
| **Path traversal** | Uploaded files processed in memory or temp dir, deleted on completion |

---

## Security Headers

Served on every response:

```
Content-Security-Policy: default-src 'self'; script-src 'self'; ...
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
```

---

## Officer Access Control

- Each officer is scoped to a unit (Range / District / Station)
- Jurisdiction enforced at the query layer — officers cannot retrieve cases outside their unit tree
- Cross-jurisdiction access requires Supervisor approval (logged to audit trail)
- All case views, status changes, and exports create an immutable `audit_log` row

---

## APK Analysis Safety

- ZIP bomb check: uncompressed/compressed ratio before any extraction
- Magic bytes verification: `PK\x03\x04` required
- `AndroidManifest.xml` and `classes.dex` presence verified before analysis
- All files processed in a temp directory, deleted on completion
- No network access during analysis
- No APK is ever executed or installed

---

## Known Attack Vectors (stated limitations)

| Vector | Current Status |
|---|---|
| JS-rendered phishing pages | Thin content — stated in output, not silently clean |
| Heavily obfuscated APKs | Fewer string findings — stated as limitation |
| RDAP rate limiting | Degrades to "domain age unknown" — never fails analysis |
| AI provider outage | Full offline rule fallback — no degradation in verdict quality |
