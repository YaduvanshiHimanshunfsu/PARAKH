import { Card, CardHeader, Icon, IdentifierChip, RiskBadge } from '../../../design/ui'
import { toRiskLevel } from '../../../design/vocab'
import { AUTH_STATUS, EMAIL_TYPE, IDENTIFIER_NAME, TACTIC, hindiLabel, label } from '../../../content/labels'
import { highlightSegments } from '../../../lib/highlight'
import { detectIdentifiers } from '../../../lib/identifiers'

const SEVERITY_TONE = {
  HIGH: 'bg-risk-high-bg text-risk-high-ink',
  MEDIUM: 'bg-risk-medium-bg text-risk-medium-ink',
  LOW: 'bg-risk-low-bg text-risk-low-ink',
}

/** The citizen's own text with the flagged phrases highlighted. */
export function HighlightedInput({ text, redFlags }) {
  if (!text) return null
  const segments = highlightSegments(text, redFlags.map((flag) => flag.phrase))
  const chips = detectIdentifiers(text).slice(0, 10)
  const marked = segments.some((segment) => segment.flag !== null)
  return (
    <Card className="p-5">
      <CardHeader title="What you checked" hindi="आपने क्या जाँचा" />
      <p className="mt-3 whitespace-pre-wrap break-words rounded-chip bg-canvas p-4 text-body-md leading-relaxed text-ink">
        {segments.map((segment, index) =>
          segment.flag === null ? (
            <span key={index}>{segment.text}</span>
          ) : (
            <mark key={index} className="rounded bg-risk-high-bg px-0.5 font-semibold text-risk-high-ink underline decoration-risk-high decoration-2 underline-offset-2">
              {segment.text}
            </mark>
          ),
        )}
      </p>
      {marked && <p className="mt-2 text-body-sm text-ink-3">Highlighted words are the warning signs explained below.</p>}
      {chips.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {chips.map((chip) => (
            <IdentifierChip key={`${chip.type}:${chip.value}`} type={chip.type} value={chip.value} />
          ))}
        </div>
      )}
    </Card>
  )
}

export function RedFlagList({ redFlags, tactics }) {
  if (!redFlags.length && !tactics.length) return null
  return (
    <Card className="p-5">
      <CardHeader title="Why PARAKH says this" hindi="यह क्यों कहा गया" />
      {tactics.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {tactics.map((tactic) => (
            <span key={tactic} className="inline-flex items-center gap-1 rounded-chip bg-accent-tint px-2.5 py-1 text-body-sm font-semibold text-accent-strong">
              <Icon name="psychology" size={16} /> {label(TACTIC, tactic)}
              <span className="hi font-normal" lang="hi">· {hindiLabel(TACTIC, tactic)}</span>
            </span>
          ))}
        </div>
      )}
      <ol className="mt-4 space-y-3">
        {redFlags.map((flag, index) => (
          <li key={`${flag.phrase}-${index}`} className="flex gap-3">
            <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-body-sm font-bold ${SEVERITY_TONE[flag.severity] || SEVERITY_TONE.HIGH}`}>
              {index + 1}
            </span>
            <div className="min-w-0">
              <p className="break-words font-mono text-body-sm font-semibold text-ink">{flag.phrase}</p>
              <p className="text-body-sm text-ink-2">{flag.explanation}</p>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  )
}

export function ActionSteps({ actions, title = 'What to do now', hindi = 'अब क्या करें' }) {
  if (!actions.length) return null
  return (
    <Card className="p-5">
      <CardHeader title={title} hindi={hindi} />
      <ol className="mt-3 space-y-2">
        {actions.map((step, index) => (
          <li key={index} className="flex gap-3 text-body-md text-ink">
            <Icon name="check_circle" className="mt-0.5 shrink-0 text-risk-low" filled size={20} />
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </Card>
  )
}

const TLS_TEXT = {
  VALID: ['Valid HTTPS certificate', 'LOW'],
  INVALID: ['Invalid HTTPS certificate', 'HIGH'],
  NOT_APPLICABLE: ['No HTTPS (plain http)', 'MEDIUM'],
  UNREACHABLE: ['Site did not answer', 'UNKNOWN'],
  NOT_CHECKED: ['Certificate not checked', 'UNKNOWN'],
}

export function UrlAnalysisCard({ analysis, compact = false }) {
  const level = toRiskLevel(analysis.risk_level)
  const [tlsText, tlsLevel] = TLS_TEXT[analysis.tls?.status] || TLS_TEXT.NOT_CHECKED
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-label-ui uppercase text-ink-3">Link check</p>
          <p className="break-all font-mono text-body-md font-semibold text-ink">{analysis.host || analysis.original_url}</p>
          {analysis.registered_domain && analysis.registered_domain !== analysis.host && (
            <p className="text-body-sm text-ink-2">
              Registered domain: <span className="font-mono">{analysis.registered_domain}</span>
            </p>
          )}
        </div>
        <RiskBadge level={level} score={analysis.risk_score} />
      </div>
      {!compact && <p className="mt-3 text-body-md text-ink-2">{analysis.summary}</p>}
      <dl className="mt-4 grid gap-2 sm:grid-cols-2">
        <div className="rounded-chip bg-canvas p-3">
          <dt className="text-label-ui uppercase text-ink-3">HTTPS</dt>
          <dd className="mt-1 flex items-center gap-1.5 text-body-sm text-ink">
            <RiskBadge level={tlsLevel} className="!px-1.5" /> {tlsText}
          </dd>
          {analysis.tls?.issuer && <dd className="mt-1 break-words text-body-sm text-ink-3">Issuer: {analysis.tls.issuer}</dd>}
        </div>
        <div className="rounded-chip bg-canvas p-3">
          <dt className="text-label-ui uppercase text-ink-3">Reputation lists</dt>
          {analysis.reputation?.length ? (
            analysis.reputation.map((item) => (
              <dd key={item.provider} className="mt-1 text-body-sm text-ink">
                <span className="font-semibold">{item.provider}:</span>{' '}
                {item.status === 'FLAGGED' ? 'Flagged' : item.status === 'NO_KNOWN_LISTING' ? 'No known listing' : item.status === 'ERROR' ? 'Lookup failed' : 'Not checked'}
                {item.threat_types?.length > 0 && <span className="text-ink-3"> ({item.threat_types.join(', ')})</span>}
              </dd>
            ))
          ) : (
            <dd className="mt-1 text-body-sm text-ink-3">No reputation service is configured on this server.</dd>
          )}
        </div>
      </dl>
      {analysis.site_profile && (
        <div className="mt-3 rounded-chip border border-line p-3 text-body-sm">
          <p className="font-semibold text-ink">{analysis.site_profile.name || 'Known site'} — {analysis.site_profile.description}</p>
          <p className="mt-1 text-ink-2">{analysis.site_profile.verification_note}</p>
        </div>
      )}
      {compact && analysis.signals?.length > 0 && (
        <ul className="mt-3 space-y-1 text-body-sm text-ink-2">
          {analysis.signals.slice(0, 4).map((signal) => (
            <li key={signal.code} className="flex gap-2">
              <Icon name="flag" size={16} className="mt-0.5 shrink-0 text-risk-high-ink" /> {signal.explanation}
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

export function EmailEvidence({ result }) {
  const auth = result.authentication
  const rows = [
    ['SPF', auth.spf],
    ['DKIM', auth.dkim],
    ['DMARC', auth.dmarc],
    ['Alignment', auth.alignment],
  ]
  return (
    <Card className="p-5">
      <CardHeader title="Sender and authentication" hindi="भेजने वाला और प्रमाणीकरण" eyebrow={EMAIL_TYPE[result.email_type]} />
      <dl className="mt-3 grid gap-2 text-body-sm sm:grid-cols-2">
        <div className="min-w-0 rounded-chip bg-canvas p-3">
          <dt className="text-label-ui uppercase text-ink-3">From</dt>
          <dd className="break-words text-ink">
            {result.sender?.display_name && <span className="font-semibold">{result.sender.display_name} </span>}
            <span className="font-mono">{result.sender?.address || 'Not given'}</span>
          </dd>
        </div>
        {result.reply_to?.address && (
          <div className="min-w-0 rounded-chip bg-canvas p-3">
            <dt className="text-label-ui uppercase text-ink-3">Replies go to</dt>
            <dd className="break-words font-mono text-ink">{result.reply_to.address}</dd>
          </div>
        )}
      </dl>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {rows.map(([name, status]) => {
          const [text, level] = AUTH_STATUS[status] || [status, 'UNKNOWN']
          return (
            <div key={name} className="rounded-chip border border-line p-3 text-center">
              <p className="text-label-ui uppercase text-ink-3">{name}</p>
              <RiskBadge level={level} className="mt-1" />
              <p className="mt-1 text-body-sm text-ink-2">{text}</p>
            </div>
          )
        })}
      </div>
      <p className="mt-2 text-body-sm text-ink-3">Source: {auth.source}</p>
      {result.attachments?.length > 0 && (
        <div className="mt-4">
          <p className="text-label-ui uppercase text-ink-3">Attachments (not opened)</p>
          <ul className="mt-1 space-y-1">
            {result.attachments.map((attachment, index) => (
              <li key={index} className="flex flex-wrap items-center gap-2 text-body-sm">
                <RiskBadge level={toRiskLevel(attachment.risk)} />
                <span className="font-mono">{attachment.filename || attachment.content_type}</span>
                <span className="text-ink-2">— {attachment.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  )
}

export function IdentifierFacts({ result }) {
  const name = IDENTIFIER_NAME[result.type] || 'identifier'
  return (
    <Card className="p-5">
      <CardHeader title="What we found" hindi="क्या मिला" />
      {result.type ? (
        <div className="mt-3 space-y-3">
          <IdentifierChip type={result.type} value={result.value} />
          <ul className="space-y-2 text-body-md text-ink">
            <li className="flex gap-2">
              <Icon name="folder_shared" className="shrink-0 text-primary" />
              {result.reported_case_count > 0
                ? `This ${name} appears in ${result.reported_case_count} officer-verified high-risk case${result.reported_case_count === 1 ? '' : 's'}.`
                : `This ${name} is not in any officer-verified high-risk case.`}
            </li>
            <li className="flex gap-2">
              <Icon name="block" className="shrink-0 text-primary" />
              {result.blacklisted
                ? `It is on the reviewed blacklist${result.blacklist_source ? ` (${result.blacklist_source})` : ''}.`
                : 'It is not on the reviewed blacklist.'}
            </li>
          </ul>
        </div>
      ) : (
        <p className="mt-3 text-body-md text-ink-2">We could not recognise a UPI ID, phone number, link or account number in what you typed.</p>
      )}
    </Card>
  )
}

export function Limitations({ items, source, notice }) {
  if (!items.length && !source && !notice) return null
  return (
    <div className="rounded-card border border-line bg-surface-container-low p-4 text-body-sm text-ink-2">
      <p className="flex items-center gap-1.5 font-semibold text-ink">
        <Icon name="info" size={18} /> Limits of this check
      </p>
      <ul className="mt-1 list-disc space-y-0.5 pl-5">
        {source === 'RULE_FALLBACK' && <li>Checked with PARAKH’s offline rules (the AI service was not used).</li>}
        {source === 'AI' && <li>Checked with the AI service. AI can be wrong; read the reasons above.</li>}
        {notice && <li>{notice}</li>}
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
        <li>PARAKH gives guidance, not a legal finding. When in doubt, call 1930.</li>
      </ul>
    </div>
  )
}
