import { describe, expect, it } from 'vitest'
import en from '../content/en.json'
import hi from '../content/hi.json'
import { translate } from './i18n'
import { redactSensitiveText } from './redaction'
import { toRiskLevel } from '../design/vocab'

describe('i18n', () => {
  const dictionaries = { en, hi }
  it('uses Hindi when present', () => {
    expect(translate(dictionaries, 'hi', 'nav.check')).toBe('जाँचें')
  })
  it('falls back to English for missing Hindi keys', () => {
    expect(translate(dictionaries, 'hi', 'officer.nav.cases')).toBe('Cases')
  })
  it('returns the key itself only when no dictionary has it', () => {
    expect(translate(dictionaries, 'en', 'no.such.key')).toBe('no.such.key')
  })
  it('interpolates variables', () => {
    expect(translate(dictionaries, 'en', 'officer.signed_in_as', { name: 'sho.cyber' })).toBe('Signed in as sho.cyber')
  })
  it('every Hindi key exists in English', () => {
    expect(Object.keys(hi).filter((key) => !(key in en))).toEqual([])
  })
})

describe('redaction', () => {
  it('masks secrets and identifiers while keeping context', () => {
    const output = redactSensitiveText(
      'Call +91 9876543210, pay user.name@oksbi, email anna@example.com. OTP: 123456. Visit https://bank.example/pay?token=secret',
    )
    expect(output).toMatch(/OTP: \[secret removed\]/)
    expect(output).toMatch(/\[private link data removed\]/)
    expect(output).not.toMatch(/9876543210|123456|token=secret/)
  })
})

describe('toRiskLevel', () => {
  it.each([
    ['SCAM', 'HIGH'],
    ['CRITICAL', 'HIGH'],
    ['high', 'HIGH'],
    ['SUSPICIOUS', 'MEDIUM'],
    ['SAFE', 'LOW'],
    ['LOW', 'LOW'],
    ['UNKNOWN', 'UNKNOWN'],
    [undefined, 'UNKNOWN'],
  ])('%s → %s', (input, expected) => {
    expect(toRiskLevel(input)).toBe(expected)
  })
})
