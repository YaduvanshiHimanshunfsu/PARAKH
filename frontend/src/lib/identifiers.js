// Client-side identifier detection for live chips and the officer search box.
//
// This is a *preview*: the server extractor (app/services/identifier_extractor.py)
// is the source of truth. The patterns, specificity order and normalisation
// below mirror it for the types the UI previews, and both implementations are
// pinned to the same vectors in tests/fixtures/identifier_vectors.json so they
// cannot silently drift. Bank accounts, Bitcoin and Android packages need
// server-side context checks and are intentionally not previewed here.

export const CLIENT_TYPES = ['URL', 'EMAIL', 'TELEGRAM', 'CRYPTO_ETH', 'IFSC', 'UPI', 'PHONE', 'IP', 'DOMAIN']

const CONTEXT_WINDOW = 60
const ACCOUNT_LABEL = /(?:\ba\/?c|\bacc(?:oun)?t|\bacct|\bbeneficiary)(?:\s*(?:no|number|num))?\.?\s*[:#-]?\s*$/i
const VERSION_CONTEXT = /(?:version|v\d|build|release|sdk|schema)\s*$/i
const DOMAIN_TLDS =
  'com|in|net|org|co|io|xyz|top|click|link|info|biz|online|site|app|shop|live|club|vip|win|bet|me|ru|cn|uk|us|tk|ml|gq|work|pro'

const digits = (value) => value.replace(/\D/g, '')

function normalisePhone(raw) {
  let d = digits(raw)
  if (d.length > 10 && d.startsWith('91')) d = d.slice(2)
  if (d.length > 10 && d.startsWith('0')) d = d.replace(/^0+/, '')
  return `+91${d.slice(-10)}`
}

function normaliseUrl(raw) {
  let value = raw.trim().replace(/[.,;:!?)"']+$/, '')
  if (!value.includes('://')) value = `https://${value}`
  return value.toLowerCase()
}

// [type, regex (global), specificity, normaliser] — same order and numbers as the server.
const PATTERNS = [
  ['URL', /\b(?:https?:\/\/|www\.)[^\s<>"'`]{3,2000}/gi, 100, normaliseUrl],
  ['EMAIL', /\b[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,200}\.[A-Za-z]{2,24}\b/g, 100, (r) => r.trim().toLowerCase()],
  [
    'TELEGRAM',
    /\b(?:https?:\/\/)?t\.me\/(?:joinchat\/)?[A-Za-z0-9_+-]{3,64}\b/gi,
    110,
    (r) => r.trim().toLowerCase().replace('https://', '').replace('http://', ''),
  ],
  ['CRYPTO_ETH', /\b0x[a-fA-F0-9]{40}\b/g, 100, (r) => r.trim().toLowerCase()],
  ['IFSC', /\b[A-Z]{4}0[A-Z0-9]{6}\b/g, 95, (r) => r.trim().toUpperCase()],
  ['UPI', /\b[A-Za-z0-9][A-Za-z0-9._-]{1,63}@[A-Za-z]{2,24}\b/g, 70, (r) => r.trim().toLowerCase()],
  ['PHONE', /(?<![\d@])(?<!\d\.)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?![\d@])(?!\.\d)/g, 90, normalisePhone],
  ['IP', /(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])/g, 95, (r) => r.trim()],
  [
    'DOMAIN',
    new RegExp(`\\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+(?:${DOMAIN_TLDS})\\b`, 'gi'),
    80,
    (r) => r.trim().replace(/\.$/, '').toLowerCase(),
  ],
]

function parseIpv4(value) {
  const parts = value.split('.')
  if (parts.length !== 4) return null
  const octets = parts.map((part) => (/^\d{1,3}$/.test(part) ? Number(part) : NaN))
  if (octets.some((o) => Number.isNaN(o) || o > 255)) return null
  if (parts.some((part) => part.length > 1 && part.startsWith('0'))) return null
  return octets
}

// Mirrors Python's ipaddress checks for the ranges that matter in scam text.
function isNonPublicIp(o) {
  const [a, b] = o
  return (
    a === 0 || a === 10 || a === 127 || a >= 224 ||
    (a === 100 && b >= 64 && b <= 127) ||
    (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    (a === 192 && b === 0) ||
    (a === 198 && (b === 18 || b === 19)) ||
    (a === 198 && b === 51) || (a === 203 && b === 0)
  )
}

function accept(type, raw, value, text, start) {
  if (type === 'UPI') return !value.split('@').pop().includes('.')
  if (type === 'IP') {
    const octets = parseIpv4(raw)
    if (!octets || isNonPublicIp(octets)) return false
    return !VERSION_CONTEXT.test(text.slice(Math.max(0, start - 20), start))
  }
  if (type === 'PHONE') {
    const count = digits(raw).length
    if (count < 10 || count > 12) return false
    return !(!raw.includes('+') && ACCOUNT_LABEL.test(text.slice(Math.max(0, start - 30), start)))
  }
  if (type === 'IFSC') return value[4] === '0'
  return true
}

function contextFor(text, start, end) {
  const left = Math.max(0, start - CONTEXT_WINDOW)
  const right = Math.min(text.length, end + CONTEXT_WINDOW)
  const snippet = text.slice(left, right).replace(/\s+/g, ' ').trim()
  return `${left > 0 ? '…' : ''}${snippet}${right < text.length ? '…' : ''}`.slice(0, 300)
}

/** Detect identifiers in `text`. Returns [{type, value, raw, start, end, context}]. */
export function detectIdentifiers(text) {
  if (!text || !text.trim()) return []
  const spans = []
  for (const [type, pattern, specificity, normalise] of PATTERNS) {
    pattern.lastIndex = 0
    for (const match of text.matchAll(pattern)) {
      const raw = match[0]
      const value = normalise(raw)
      if (!value) continue
      const start = match.index
      const end = start + raw.length
      if (!accept(type, raw, value, text, start)) continue
      spans.push({ type, raw, value, start, end, specificity })
    }
  }

  // Overlap resolution: more specific pattern first, then the longer match.
  spans.sort((a, b) => b.specificity - a.specificity || b.end - b.start - (a.end - a.start) || a.start - b.start)
  const kept = []
  for (const span of spans) {
    if (kept.some((k) => span.start < k.end && k.start < span.end)) continue
    kept.push(span)
  }

  // A URL implies its host, so linking works whether a case cites the URL or the domain.
  for (const span of [...kept]) {
    if (span.type !== 'URL') continue
    let host = span.value.replace(/^https?:\/\//, '').split('/')[0].split(':')[0]
    host = host.replace(/^www\./, '')
    if (!host || !host.includes('.')) continue
    const octets = parseIpv4(host)
    if (octets && isNonPublicIp(octets)) continue
    const hostType = octets ? 'IP' : 'DOMAIN'
    if (!kept.some((k) => k.type === hostType && k.value === host)) {
      kept.push({ type: hostType, raw: host, value: host, start: span.start, end: span.end, specificity: 0 })
    }
  }

  kept.sort((a, b) => a.start - b.start)
  const seen = new Set()
  const results = []
  for (const span of kept) {
    const key = `${span.type}:${span.value}`
    if (seen.has(key)) continue
    seen.add(key)
    results.push({
      type: span.type,
      value: span.value,
      raw: span.raw,
      start: span.start,
      end: span.end,
      context: contextFor(text, span.start, span.end),
    })
  }
  return results
}

/** Best single guess for a search box: the identifier type a pasted value looks like. */
export function guessIdentifierType(value) {
  const trimmed = (value || '').trim()
  if (!trimmed) return null
  const found = detectIdentifiers(trimmed)
  const whole = found.find((item) => item.start === 0 && item.end >= trimmed.length - 1)
  return whole ? whole.type : null
}
