import { describe, expect, it } from 'vitest'
import { explainPayloadFlags, normaliseResult } from './normalise'
import { highlightSegments } from '../../../lib/highlight'
import { EXPOSURE, SAFE_ACTION, SAFETY_DECISION, SCAM_CATEGORY, TACTIC } from '../../../content/labels'

const at = '2026-11-24T10:00:00.000Z'

describe('highlightSegments', () => {
  it('marks every case-insensitive occurrence and keeps the text intact', () => {
    const text = 'Update KYC now. kyc expires today. Update now!'
    const segments = highlightSegments(text, ['kyc', 'update now'])
    expect(segments.map((s) => s.text).join('')).toBe(text)
    expect(segments.filter((s) => s.flag !== null).map((s) => s.text)).toEqual(['KYC', 'kyc', 'Update now'])
  })

  it('merges overlapping phrases into one highlight', () => {
    const segments = highlightSegments('call 9988776655 now', ['call 9988', '9988776655'])
    expect(segments.filter((s) => s.flag !== null).map((s) => s.text)).toEqual(['call 9988776655'])
  })

  it('ignores empty and one-letter phrases', () => {
    expect(highlightSegments('abc', ['', 'a', null])).toEqual([{ text: 'abc', flag: null }])
  })
})

describe('normaliseResult', () => {
  it('returns null when there is no result', () => {
    expect(normaliseResult(null)).toBeNull()
    expect(normaliseResult({ kind: 'message', input: {}, result: null })).toBeNull()
  })

  it('maps a message analysis to a HIGH verdict with a report payload', () => {
    const model = normaliseResult({
      kind: 'message',
      at,
      input: { text: 'Your bill is unpaid, call 9988776655', language: 'auto' },
      result: {
        verdict: 'SCAM',
        confidence: 91,
        scam_category: 'UTILITY_BILL_SCAM',
        severity: 'HIGH',
        psychological_tactics: ['FALSE_URGENCY'],
        red_flags: [{ phrase: 'bill is unpaid', explanation: 'Pressure about an unpaid bill.' }],
        action_steps: ['Do not call the number.'],
        hindi_summary: 'यह ठगी है।',
        analysis_source: 'RULE_FALLBACK',
        url_analyses: [],
      },
    })
    expect(model.level).toBe('HIGH')
    expect(model.score).toBe(91)
    expect(model.title).toBe('This looks like a scam')
    expect(model.report).toEqual({ artifact_type: 'MESSAGE', content: 'Your bill is unpaid, call 9988776655' })
    expect(model.source).toBe('RULE_FALLBACK')
  })

  it('never calls a SAFE verdict "safe" — it says no signs were found', () => {
    const model = normaliseResult({
      kind: 'message',
      at,
      input: { text: 'Lunch at 1?' },
      result: { verdict: 'SAFE', confidence: 80, scam_category: 'UNKNOWN', red_flags: [], action_steps: ['Stay alert.'], hindi_summary: 'ठीक है' },
    })
    expect(model.level).toBe('LOW')
    expect(model.title).toBe('No common scam signs found')
  })

  it('maps URL signals to red flags and keeps the risk score', () => {
    const model = normaliseResult({
      kind: 'url',
      at,
      input: { url: 'https://sbi-verify-kyc.in/urgent' },
      result: {
        original_url: 'https://sbi-verify-kyc.in/urgent',
        risk_level: 'CRITICAL',
        risk_score: 88,
        signals: [{ code: 'BRAND_LOOKALIKE', severity: 'HIGH', explanation: 'Uses a bank name in an unofficial domain.' }],
        tls: { status: 'NOT_CHECKED' },
        reputation: [],
        summary: 'Looks like a fake bank page.',
        limitations: 'The page was not opened.',
      },
    })
    expect(model.level).toBe('HIGH')
    expect(model.score).toBe(88)
    expect(model.redFlags[0]).toMatchObject({ phrase: 'BRAND_LOOKALIKE', severity: 'HIGH' })
    expect(model.limitations).toEqual(['The page was not opened.'])
    expect(model.report.artifact_type).toBe('URL')
  })

  it('maps QR safety decisions and reports a UPI payload as a message', () => {
    const model = normaliseResult({
      kind: 'qr',
      at,
      input: { payload: 'upi://pay?pa=richplan@ybl' },
      result: {
        payload_kind: 'UPI_PAYMENT',
        decision: 'STOP_NOW',
        title: 'This QR sends money',
        simple_explanation: 'Scanning this QR pays money to someone.',
        hindi_explanation: 'यह क्यूआर पैसे भेजता है।',
        actions: ['Do not scan to receive money.'],
        upi_id: 'richplan@ybl',
      },
    })
    expect(model.level).toBe('HIGH')
    expect(model.title).toBe('This QR sends money')
    expect(model.category).toBe('UPI_FRAUD')
    expect(model.score).toBeNull()
    expect(model.report).toEqual({ artifact_type: 'MESSAGE', content: 'upi://pay?pa=richplan@ybl' })
  })

  it('builds an email report from pasted fields', () => {
    const model = normaliseResult({
      kind: 'email',
      at,
      input: { email: { sender: 'a@b.in', subject: 'KYC', body: 'Update now' } },
      result: {
        verdict: 'SUSPICIOUS',
        confidence: 60,
        scam_category: 'KYC_SCAM',
        authentication: { spf: 'NONE', dkim: 'NONE', dmarc: 'NONE', alignment: 'NONE', source: 'pasted' },
        red_flags: [],
        action_steps: ['Verify with the bank.'],
        hindi_summary: 'संदिग्ध',
        limitations: ['Headers were not provided.'],
      },
    })
    expect(model.level).toBe('MEDIUM')
    expect(model.report.content).toBe('From: a@b.in\nSubject: KYC\n\nUpdate now')
  })

  it('maps identifier checks', () => {
    const model = normaliseResult({
      kind: 'identifier',
      at,
      input: { value: 'richplan@ybl' },
      result: { input: 'richplan@ybl', type: 'UPI', value: 'richplan@ybl', risk_level: 'HIGH', reported_case_count: 4, advice: ['Do not pay.'], limitations: 'x'.repeat(20) },
    })
    expect(model.level).toBe('HIGH')
    expect(model.actions).toEqual(['Do not pay.'])
    expect(model.score).toBeNull()
  })
})

describe('explainPayloadFlags', () => {
  it('trims to the /explain-simply contract', () => {
    const flags = Array.from({ length: 9 }, (_, i) => ({ phrase: 'p'.repeat(200), explanation: `reason ${i}`, severity: 'HIGH' }))
    const out = explainPayloadFlags([{ phrase: 'x', explanation: 'no' }, ...flags])
    expect(out).toHaveLength(6)
    expect(out[0].phrase).toHaveLength(160)
    expect(Object.keys(out[0])).toEqual(['phrase', 'explanation'])
  })
})

describe('labels match the backend enums', () => {
  it('covers every enum value in app/schemas.py', () => {
    expect(Object.keys(SCAM_CATEGORY)).toHaveLength(16)
    expect(Object.keys(TACTIC)).toHaveLength(8)
    expect(Object.keys(EXPOSURE)).toEqual([
      'RECEIVED_ONLY', 'CLICKED_LINK', 'SHARED_PERSONAL_INFO', 'SHARED_SECRET', 'INSTALLED_APP_OR_SCREEN_SHARE', 'SENT_MONEY',
    ])
    expect(Object.keys(SAFE_ACTION)).toEqual([
      'CLICK_LINK', 'CALL_NUMBER', 'PAY_MONEY', 'INSTALL_APP', 'SHARE_OTP', 'SCAN_OR_PAY_QR', 'OPEN_ATTACHMENT',
    ])
    expect(Object.keys(SAFETY_DECISION)).toEqual(['STOP_NOW', 'VERIFY_FIRST', 'LOWER_RISK_STILL_VERIFY'])
  })
})
