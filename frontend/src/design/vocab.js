// Shared visual vocabulary: identifier types and risk levels.
// Keys match the backend enums in app/schemas.py (IdentifierType, RiskLevel,
// Verdict, UrlRiskLevel) so API values can be passed straight through.

export const IDENTIFIER_META = {
  UPI: { label: 'UPI', color: 'var(--color-id-upi)', icon: 'account_balance_wallet' },
  PHONE: { label: 'Phone', color: 'var(--color-id-phone)', icon: 'call' },
  BANK_ACCOUNT: { label: 'Bank A/c', color: 'var(--color-id-bank)', icon: 'account_balance' },
  IFSC: { label: 'IFSC', color: 'var(--color-id-ifsc)', icon: 'pin' },
  DOMAIN: { label: 'Domain', color: 'var(--color-id-domain)', icon: 'language' },
  URL: { label: 'URL', color: 'var(--color-id-url)', icon: 'link' },
  EMAIL: { label: 'Email', color: 'var(--color-id-email)', icon: 'alternate_email' },
  TELEGRAM: { label: 'Telegram', color: 'var(--color-id-telegram)', icon: 'send' },
  IP: { label: 'IP', color: 'var(--color-id-ip)', icon: 'dns' },
  CRYPTO_BTC: { label: 'BTC', color: 'var(--color-id-crypto)', icon: 'currency_bitcoin' },
  CRYPTO_ETH: { label: 'ETH', color: 'var(--color-id-crypto)', icon: 'currency_bitcoin' },
  PACKAGE: { label: 'App', color: 'var(--color-id-package)', icon: 'android' },
  CERT_SHA256: { label: 'Cert', color: 'var(--color-id-cert)', icon: 'verified' },
  ICON_PHASH: { label: 'Icon hash', color: 'var(--color-id-cert)', icon: 'image' },
}

export const UNKNOWN_IDENTIFIER = { label: 'ID', color: 'var(--color-ink-2)', icon: 'tag' }

export function identifierMeta(type) {
  return IDENTIFIER_META[type] || { ...UNKNOWN_IDENTIFIER, label: type || 'ID' }
}

// Risk is always shown as tint + ink + icon + text (DESIGN.md tri-signal rule).
export const RISK_META = {
  HIGH: {
    label: 'High risk',
    hindi: 'उच्च जोखिम',
    icon: 'gpp_maybe',
    bg: 'var(--color-risk-high-bg)',
    ink: 'var(--color-risk-high-ink)',
    line: 'var(--color-risk-high)',
  },
  MEDIUM: {
    label: 'Medium risk',
    hindi: 'मध्यम जोखिम',
    icon: 'warning',
    bg: 'var(--color-risk-medium-bg)',
    ink: 'var(--color-risk-medium-ink)',
    line: 'var(--color-risk-medium)',
  },
  LOW: {
    label: 'Low risk',
    hindi: 'कम जोखिम',
    icon: 'verified_user',
    bg: 'var(--color-risk-low-bg)',
    ink: 'var(--color-risk-low-ink)',
    line: 'var(--color-risk-low)',
  },
  UNKNOWN: {
    label: 'Not assessed',
    hindi: 'आकलन नहीं',
    icon: 'help',
    bg: '#f1f5f9',
    ink: 'var(--color-ink-2)',
    line: 'var(--color-line)',
  },
}

/**
 * Normalise any backend risk vocabulary to LOW / MEDIUM / HIGH / UNKNOWN.
 * Accepts RiskLevel, Verdict (SCAM/SUSPICIOUS/SAFE) and UrlRiskLevel (incl. CRITICAL).
 */
export function toRiskLevel(value) {
  switch (String(value || '').toUpperCase()) {
    case 'HIGH':
    case 'CRITICAL':
    case 'SCAM':
      return 'HIGH'
    case 'MEDIUM':
    case 'SUSPICIOUS':
      return 'MEDIUM'
    case 'LOW':
    case 'SAFE':
      return 'LOW'
    default:
      return 'UNKNOWN'
  }
}

export function riskMeta(value) {
  return RISK_META[toRiskLevel(value)]
}
