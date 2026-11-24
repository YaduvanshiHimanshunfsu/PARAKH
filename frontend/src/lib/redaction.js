// Masks credentials and personal identifiers in text that a citizen exports or
// shares (evidence locker, "share warning"). Officer full reports are produced
// server-side by app/services/report_builder.py and are not redacted here.

const EMAIL = /\b([A-Z0-9._%+-]+)@([A-Z0-9.-]+\.[A-Z]{2,})\b/gi
const UPI = /\b([a-z0-9._-]{2,})@([a-z][a-z0-9-]{1,})\b/gi
const PHONE = /(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)/g
const CARD = /(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)/g
const AADHAAR = /(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)/g
const URL_PATTERN = /\bhttps?:\/\/[^\s<>()]+/gi
const SECRET = /\b(otp|password|passcode|pin|cvv|security\s*code)\s*[:=-]?\s*\d{3,12}\b/gi

function keepEdges(value, start = 1, end = 2) {
  if (value.length <= start + end) return '[redacted]'
  return `${value.slice(0, start)}${'•'.repeat(Math.min(6, value.length - start - end))}${value.slice(-end)}`
}

function maskUrl(value) {
  try {
    const parsed = new URL(value)
    const extra = parsed.search || parsed.hash ? '[private link data removed]' : ''
    return `${parsed.protocol}//${parsed.host}${parsed.pathname || '/'}${extra}`
  } catch {
    return '[link redacted]'
  }
}

export function redactSensitiveText(value = '') {
  return String(value)
    .replace(URL_PATTERN, maskUrl)
    .replace(SECRET, '$1: [secret removed]')
    .replace(EMAIL, (_match, user, domain) => `${keepEdges(user)}@${domain}`)
    .replace(UPI, (_match, user, provider) => `${keepEdges(user)}@${provider}`)
    .replace(AADHAAR, '[identity number removed]')
    .replace(CARD, '[card number removed]')
    .replace(PHONE, (phone) => `[phone ${keepEdges(phone.replace(/\D/g, ''), 2, 2)}]`)
}
