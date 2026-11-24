# Security Policy

PARAKH handles fraud reports and police case data. We take security reports
seriously and would rather hear about a problem early.

> This file is the **reporting policy**. For how the system is secured —
> the privacy guarantee, authentication, SSRF guards and the audit chain —
> see [docs/SECURITY.md](docs/SECURITY.md).

## Reporting a vulnerability

**Please do not open a public issue.** Contact the maintainers privately
through the channel listed in the hackathon submission, with:

- what the issue is and where,
- how to reproduce it,
- what an attacker could achieve.

We will acknowledge, confirm, and tell you when it is fixed.

## What is in scope

- Authentication, session handling and the account lockout
- The role, permission and **jurisdiction scoping** model — in particular, any
  way for an officer to read a case outside their unit
- The citizen endpoints, which are unauthenticated by design
- The audit hash chain
- SSRF protection in the website fetcher and URL checker
- File handling for uploaded APKs, images and audio
- Any way to make the interface state something untrue

## Known limitations, by design

These are deliberate and documented, not oversights:

| Limitation | Why |
|---|---|
| An administrator with direct database access can rewrite the whole audit chain | The chain makes *partial* tampering detectable, which is what an evidence trail needs. Full protection needs an external notary (Phase E). |
| Demo accounts share one password | Demonstration only, loudly labelled. A deployment issues one password per officer, set at first sign-in. |
| Citizen endpoints are unauthenticated | The product requires it: a victim must be able to check a message without an account. They are rate-limited and store nothing without explicit consent. |
| `trust_proxy_headers` defaults to **off** | A directly reachable server lets a client forge `X-Forwarded-For` and evade the per-IP limit. Turn it on only behind a proxy that overwrites the header. |
| Sample addressee contacts are placeholders | Real nodal-officer directories are not public. Inventing one would send a legal notice to the wrong place. |

## Handling of sensitive data

- Passwords are stored as hashes; bearer tokens are stored as hashes, never in clear.
- A Telegram bot token found in evidence is recorded with the **bot id only**;
  the token itself is masked and is never used to call the Telegram API, since
  accessing a suspect's bot with their own credential could itself be
  unauthorised access.
- The citizen evidence locker is encrypted with AES-GCM using a
  non-extractable key held in the browser. It never reaches the server.
- Citizen checks are not persisted. Only an explicitly consented report is
  stored, and it is quarantined from intelligence until an officer verifies it.

## Security controls in place

- Content-Security-Policy with `script-src 'self'` and `font-src 'self'` — no CDN
- Rate limiting per route, with a daily anonymous cap
- Account lockout with exponential back-off; optional TOTP for supervisors
- SSRF guard with DNS pinning on every outbound fetch
- Path-traversal protection on SPA file serving (regression-tested)
- Upload size and MIME validation; APKs are parsed, never executed
