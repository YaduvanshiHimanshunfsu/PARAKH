# PARAKH — System Architecture Deep-Dive

> Read this after `README.md`. It documents **why** each design decision was made, the full data flow, and the security model.

---

## 1. Design Philosophy

PARAKH is built on five principles, each of which resolved a real tension:

| Principle | Tension Resolved | ADR |
|---|---|---|
| **Offline-first** | AI enrichment is valuable but unreliable at demo time | ADR-005 |
| **Dual-mode privacy** | Citizens need privacy; officers need searchable records | ADR-001 |
| **Deterministic verdicts** | APK/website analysis must survive a dead API key | ADR-005 |
| **SSRF-safe fetching** | Website analysis needs HTTP fetching; must not probe LAN | ADR-002 |
| **SQLite-first, Postgres-ready** | Zero infra for demo; ORM-only SQL for production swap | ADR-003 |

---

## 2. Component Map

```
┌────────────────────────────────────────────────────────────────────┐
│  Citizen SPA                      Officer Console SPA              │
│  React 19 / Vite 8               React 19 / Vite 8                │
│  Civic Vigilance Light DS        Civic Vigilance Light DS         │
│  Hindi ↔ English i18n            Role/jurisdiction-aware          │
│  AES-GCM evidence locker         Campaign graph, heat-list        │
└────────────────┬──────────────────────────┬────────────────────────┘
                 │                          │
      /api/v1/parakh/*          /api/v1/investigate/*
                 │                          │
┌────────────────▼──────────────────────────▼────────────────────────┐
│                        FastAPI Application                          │
│                                                                     │
│  Middleware stack (innermost → outermost):                         │
│  RequestSizeLimitMiddleware (3.25 MB global, 60 MB APK route)      │
│  RateLimitMiddleware (20 req/min · 120/day anonymous)              │
│  SecurityHeadersMiddleware (CSP, HSTS, X-Frame, nosniff)          │
│  CORSMiddleware (ALLOWED_ORIGINS from .env)                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   Analysis Engine                           │   │
│  │                                                             │   │
│  │  ScamAnalyzer          EmailAnalyzer     QrAnalyzer         │   │
│  │  ├─ Rule Engine v2     ├─ SPF/DKIM/DMARC └─ zxing-cpp       │   │
│  │  ├─ Gemini AI          └─ Attachment risk    + URL analysis  │   │
│  │  ├─ AI Fusion Guardrail                                     │   │
│  │  └─ FallbackAnalyzer                                        │   │
│  │                                                             │   │
│  │  ApkAnalyzer              WebsiteAnalyzer                   │   │
│  │  ├─ pyaxmlparser          ├─ SSRF-guarded httpx             │   │
│  │  ├─ v1/v2/v3 certs        ├─ BeautifulSoup4                │   │
│  │  ├─ DEX string scan       ├─ Ponzi/MLM/betting rules        │   │
│  │  └─ Icon dHash            └─ zxing-cpp QR on page images    │   │
│  │                                                             │   │
│  │  URLIntelligenceService                                     │   │
│  │  ├─ 9 risk signals (NO_HTTPS, IDN, SHORTENER, etc.)         │   │
│  │  ├─ TLS certificate probe                                   │   │
│  │  ├─ RDAP domain age                                         │   │
│  │  ├─ Redirect chain (hop-by-hop, SSRF guard each hop)        │   │
│  │  └─ Blacklist match                                         │   │
│  │                                                             │   │
│  └───────────────────────┬─────────────────────────────────────┘   │
│                          │                                          │
│  IdentifierExtractor     │   (14 types, span-based dedup)          │
│  ├─ phonenumbers lib      │                                         │
│  ├─ PSP-validated UPI     │                                         │
│  ├─ BTC/ETH/TRC20 regex   │                                         │
│  └─ zxing-cpp QR payloads │                                         │
│                          │                                          │
│            ┌─────────────▼──────────────────┐                      │
│            │         CaseService             │                      │
│            │  ┌─────────────────────────┐   │                      │
│            │  │  Citizen: return only   │   │                      │
│            │  │  Officer: persist case  │   │                      │
│            │  │  + findings + identifiers│  │                      │
│            │  └─────────────────────────┘   │                      │
│            └─────────────┬──────────────────┘                      │
│                          │                                          │
│            ┌─────────────▼──────────────────┐                      │
│            │  LinkService / CampaignService  │                      │
│            │  SimHash · Identifier graph     │                      │
│            │  Campaign clustering (union-find)│                     │
│            │  Heat-list (GROUP BY, 7-day trend)│                    │
│            └─────────────┬──────────────────┘                      │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
           ┌───────────────▼──────────────────┐
           │  SQLite + aiosqlite (dev)         │
           │  PostgreSQL + asyncpg (prod)      │
           │                                  │
           │  Tables:                         │
           │  users · units · cases           │
           │  findings · identifiers          │
           │  blacklist · domain_intel        │
           │  audit_log · requisitions        │
           └──────────────────────────────────┘
```

---

## 3. The Identifier Graph

The most important data structure in PARAKH is the **identifier graph** stored in the `identifiers` table.

```
Schema: identifiers(case_id, type, value_normalized, value_raw, context)

Index: (type, value_normalized)  ← the join that powers all linking queries

Linking query (simplified):
  SELECT other.case_id, COUNT(*) as shared, SUM(weight) as score
  FROM identifiers self
  JOIN identifiers other USING (type, value_normalized)
  WHERE self.case_id = :this_case
    AND other.case_id != :this_case
    AND self.type NOT IN ('URL', 'DOMAIN')  -- low-value identifiers excluded
  GROUP BY other.case_id
  ORDER BY score DESC
```

**Weights by identifier type:**

| Type | Weight | Rationale |
|---|---|---|
| UPI ID | 10 | Unique to a fraud operator's payment account |
| Bank account + IFSC | 10 | Unique financial trace |
| Crypto wallet | 10 | On-chain traceable |
| Certificate fingerprint | 10 | Ties APKs to same developer |
| Phone number (E.164) | 7 | Shared across campaigns but still strong |
| Email address | 7 | — |
| Telegram handle | 5 | Often reused across scam groups |
| Package name | 5 | APK reuse signal |
| Domain | 3 | Shared domains are weaker (CDNs, link shorteners) |
| URL | 1 | Very common, lowest signal |

**Exclusion:** known official domains (`gov.in`, `sbi.co.in`, `hdfc.com`, etc.) are whitelisted and **never** used as linking identifiers — fixing defect D6 from baseline.

---

## 4. SimHash Similarity

Near-duplicate detection uses a custom SimHash over character 5-grams.

```python
# Why character n-grams beat word n-grams for scam SMS:
#
# Word 5-gram test on two variants of same template:
#   "Pay ₹500 registration fee"  vs  "Pay ₹200 joining fee"
#   Hamming distance: 34 bits  ← indistinguishable from unrelated messages (35)
#
# Character 5-gram test on same pair:
#   Hamming distance: 11 bits  ← clearly near-duplicate (threshold: 16)
#
# Near-duplicate threshold: Hamming ≤ 3 bits
# Campaign variant threshold: Hamming ≤ 16 bits
```

---

## 5. AI Fusion Guardrail

```
Rule Engine verdict: HIGH (confidence 85, LOAN_APP_FRAUD)
Gemini verdict:      MEDIUM (confidence 60, UNKNOWN)

AI Fusion Guardrail:
  if rule_verdict == HIGH and ai_verdict in (LOW, MEDIUM, SAFE):
      final = rule_verdict  ← AI cannot lower a HIGH rule hit
      source_tag = "RULE_OVERRIDE"
  elif ai_verdict == HIGH and rule_verdict in (LOW, MEDIUM):
      final = HIGH          ← AI can raise a low rule score
      source_tag = "AI_RAISED"
  else:
      final = max(rule_verdict, ai_verdict)
      source_tag = "FUSED"
```

This ensures the demo always produces correct, explainable results regardless of AI availability.

---

## 6. SSRF Protection

Every outbound HTTP request goes through `_public_addresses()`:

```python
# Blocked ranges (checked at EVERY redirect hop, not just the first):
# 127.0.0.0/8      (loopback)
# 10.0.0.0/8       (RFC-1918)
# 172.16.0.0/12    (RFC-1918)
# 192.168.0.0/16   (RFC-1918)
# 169.254.0.0/16   (link-local / IMDS)
# ::1              (IPv6 loopback)
# fc00::/7         (IPv6 ULA)
# fe80::/10        (IPv6 link-local)

# Redirect chain: 3 max hops, 10s total timeout, 2 MB stream cap
# User-Agent: generic browser string (not "PARAKH-Investigation/1.0")
# Content-Type: HTML/text only (rejects JSON/binary responses)
```

---

## 7. Officer Hierarchy

```
ADMIN
  └── SP (Superintendent of Police) — district scope
        └── DySP (Deputy SP) — sub-division scope
              └── SHO (Station House Officer) — station scope
                    └── IO (Investigating Officer) — case scope
                          └── Operator — submission only
```

- Each officer is assigned to a `unit` (district/station/range)
- Cases are scoped to the officer's jurisdiction
- Cross-jurisdiction access requires supervisor approval
- All access is logged to the tamper-evident `audit_log` table

---

## 8. Data Model (simplified)

```
users(id, username, password_hash, role, unit_id, totp_secret)
units(id, name, type[RANGE/DISTRICT/STATION], parent_id)

cases(id, public_case_id, artifact_type, risk_level, risk_score,
      verdict, status, source, submitted_by, created_at, notes,
      content_hash, simhash)

findings(id, case_id, code, severity, explanation, evidence_snippet)

identifiers(id, case_id, type, value_normalized, value_raw, context)

blacklist(id, type, value, source, added_at)

domain_intel(id, registered_domain, creation_date, registrar,
             fetched_at)  ← RDAP cache (TTL: 168 hours)

audit_log(id, actor_id, action, resource_type, resource_id,
          ip_address, created_at)

requisitions(id, case_id, submitted_by, approved_by, type,
             status, action_pack_json, created_at)
```
