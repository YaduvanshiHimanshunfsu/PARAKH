import { toRiskLevel } from '../../../design/vocab'
import { SAFETY_DECISION } from '../../../content/labels'

// Turns any citizen check result into one view model for the Result screen.
// Only values the backend returned are shown; nothing is invented here.

const VERDICT_TITLES = {
  HIGH: ['This looks like a scam', 'यह ठगी लगती है'],
  MEDIUM: ['Be careful — this is suspicious', 'सावधान — यह संदिग्ध है'],
  LOW: ['No common scam signs found', 'ठगी के सामान्य संकेत नहीं मिले'],
  UNKNOWN: ['We could not assess this', 'आकलन नहीं हो सका'],
}

const LEVEL_TO_VERDICT = { HIGH: 'SCAM', MEDIUM: 'SUSPICIOUS', LOW: 'SAFE', UNKNOWN: 'SUSPICIOUS' }

function asList(value) {
  if (!value) return []
  return Array.isArray(value) ? value : [value]
}

function emailContent(input) {
  const email = input?.email || {}
  if (email.raw_eml) return email.raw_eml
  const lines = []
  if (email.sender) lines.push(`From: ${email.sender}`)
  if (email.subject) lines.push(`Subject: ${email.subject}`)
  return `${lines.join('\n')}${lines.length ? '\n\n' : ''}${email.body || ''}`
}

/**
 * @returns {{
 *   kind, level, verdict, category, score, scoreLabel, title, hindiTitle,
 *   summary, hindiSummary, redFlags, tactics, actions, limitations,
 *   urlAnalyses, source, notice, inputText, report: {artifact_type, content}|null,
 *   evidenceKind, raw
 * }}
 */
export function normaliseResult(entry) {
  if (!entry?.result) return null
  const { kind, input, result } = entry
  const base = {
    kind,
    raw: result,
    at: entry.at,
    redFlags: [],
    tactics: [],
    actions: [],
    limitations: [],
    urlAnalyses: [],
    source: null,
    notice: null,
    category: 'UNKNOWN',
    score: null,
    scoreLabel: null,
    summary: '',
    hindiSummary: '',
    inputText: '',
    report: null,
    evidenceKind: 'MESSAGE',
  }

  let model
  switch (kind) {
    case 'message':
    case 'screenshot':
    case 'voice': {
      const level = toRiskLevel(result.verdict)
      model = {
        ...base,
        level,
        verdict: result.verdict,
        category: result.scam_category,
        score: result.confidence,
        scoreLabel: 'Confidence',
        summary: result.safe_explanation || '',
        hindiSummary: result.hindi_summary,
        redFlags: result.red_flags || [],
        tactics: result.psychological_tactics || [],
        actions: result.action_steps || [],
        urlAnalyses: result.url_analyses || [],
        source: result.analysis_source,
        notice: result.notice,
        inputText: input.text,
        report: { artifact_type: 'MESSAGE', content: input.text },
        evidenceKind: kind === 'voice' ? 'VOICE_TRANSCRIPT' : kind === 'screenshot' ? 'SCREENSHOT' : 'MESSAGE',
      }
      break
    }
    case 'url': {
      const level = toRiskLevel(result.risk_level)
      model = {
        ...base,
        level,
        verdict: LEVEL_TO_VERDICT[level],
        category: level === 'LOW' ? 'UNKNOWN' : 'PHISHING_LINK',
        score: result.risk_score,
        scoreLabel: 'Risk score',
        summary: result.summary,
        redFlags: (result.signals || []).map((signal) => ({ phrase: signal.code, explanation: signal.explanation, severity: signal.severity })),
        limitations: asList(result.limitations),
        urlAnalyses: [result],
        inputText: input.url,
        report: { artifact_type: 'URL', content: input.url },
        evidenceKind: 'URL',
      }
      break
    }
    case 'email': {
      const level = toRiskLevel(result.verdict)
      const content = emailContent(input)
      model = {
        ...base,
        level,
        verdict: result.verdict,
        category: result.scam_category,
        score: result.confidence,
        scoreLabel: 'Confidence',
        hindiSummary: result.hindi_summary,
        redFlags: result.red_flags || [],
        tactics: result.psychological_tactics || [],
        actions: result.action_steps || [],
        limitations: asList(result.limitations),
        urlAnalyses: result.url_analyses || [],
        source: result.analysis_source,
        inputText: input?.email?.body || '',
        report: content.trim().length >= 3 ? { artifact_type: 'EMAIL', content } : null,
        evidenceKind: 'EMAIL',
      }
      break
    }
    case 'qr': {
      const decision = SAFETY_DECISION[result.decision]
      const level = decision?.level || 'UNKNOWN'
      const urlAnalysis = result.url_analysis
      model = {
        ...base,
        level,
        verdict: LEVEL_TO_VERDICT[level],
        category: result.payload_kind === 'UPI_PAYMENT' ? 'UPI_FRAUD' : urlAnalysis ? 'PHISHING_LINK' : 'UNKNOWN',
        score: urlAnalysis ? urlAnalysis.risk_score : null,
        scoreLabel: urlAnalysis ? 'Link risk score' : null,
        title: result.title,
        summary: result.simple_explanation,
        hindiSummary: result.hindi_explanation,
        actions: result.actions || [],
        urlAnalyses: urlAnalysis ? [urlAnalysis] : [],
        inputText: input.payload,
        report: urlAnalysis
          ? { artifact_type: 'URL', content: urlAnalysis.original_url }
          : { artifact_type: 'MESSAGE', content: input.payload },
        evidenceKind: urlAnalysis ? 'URL' : 'MESSAGE',
      }
      break
    }
    case 'identifier': {
      const level = toRiskLevel(result.risk_level)
      model = {
        ...base,
        level,
        verdict: LEVEL_TO_VERDICT[level],
        category: result.type === 'UPI' ? 'UPI_FRAUD' : 'UNKNOWN',
        actions: result.advice || [],
        limitations: asList(result.limitations),
        inputText: input.value,
        report: input.value.trim().length >= 3 ? { artifact_type: 'MESSAGE', content: input.value } : null,
        evidenceKind: 'TRANSACTION_REFERENCE',
      }
      break
    }
    default:
      return null
  }

  const [title, hindiTitle] = VERDICT_TITLES[model.level] || VERDICT_TITLES.UNKNOWN
  return { ...model, title: model.title || title, hindiTitle }
}

/** Red flags in the shape /explain-simply accepts (phrase ≤160, explanation 5–320). */
export function explainPayloadFlags(redFlags) {
  return redFlags
    .filter((flag) => flag.phrase && flag.explanation && flag.explanation.length >= 5)
    .slice(0, 6)
    .map((flag) => ({ phrase: String(flag.phrase).slice(0, 160), explanation: String(flag.explanation).slice(0, 320) }))
}
