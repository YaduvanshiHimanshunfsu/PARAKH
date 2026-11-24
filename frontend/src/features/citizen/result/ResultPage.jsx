import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { ButtonLink, EmptyBlock, Icon, RiskGauge, Card } from '../../../design/ui'
import { riskMeta } from '../../../design/vocab'
import { SCAM_CATEGORY, hindiLabel, label } from '../../../content/labels'
import { useResult } from '../../../app/ResultContext'
import { normaliseResult } from './normalise'
import { ActionSteps, EmailEvidence, HighlightedInput, IdentifierFacts, Limitations, RedFlagList, UrlAnalysisCard } from './sections'
import { ExplainSimply, ExposurePicker, ReportToPolice, SafeNextStep, SaveEvidence } from './ActionsRail'

// Built from design/stitch/parakh_verification_result_high_risk_scam_alert and
// the medium/low variants. One screen serves every check type; the sections
// shown depend on what the backend actually returned.

const KIND_LABEL = {
  message: ['Message', 'sms'],
  screenshot: ['Screenshot text', 'image_search'],
  voice: ['Voice note text', 'mic'],
  url: ['Link', 'link'],
  email: ['Email', 'mail'],
  qr: ['QR code', 'qr_code_scanner'],
  identifier: ['UPI ID / number', 'account_balance_wallet'],
}

function VerdictHero({ model }) {
  const meta = riskMeta(model.level)
  const reduce = useReducedMotion()
  const [kindLabel, kindIcon] = KIND_LABEL[model.kind] || ['Check', 'search']
  const showCategory = model.category && model.category !== 'UNKNOWN' && model.level !== 'LOW'
  return (
    <motion.section
      initial={reduce ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="relative overflow-hidden rounded-hero border p-5 shadow-l2 md:p-7"
      style={{ background: meta.bg, borderColor: `color-mix(in srgb, ${meta.line} 35%, white)` }}
      aria-labelledby="verdict-title"
    >
      <div className="flex flex-col gap-5 md:flex-row md:items-center">
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 text-label-ui uppercase text-ink-2">
            <Icon name={kindIcon} size={16} /> {kindLabel} ·{' '}
            <time dateTime={model.at}>{new Date(model.at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</time>
          </p>
          <div className="mt-2 flex items-start gap-3">
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-white shadow-l1" style={{ color: meta.ink }}>
              <Icon name={meta.icon} size={28} filled />
            </span>
            <div className="min-w-0">
              <h1 id="verdict-title" className="text-headline-lg-mobile md:text-headline-lg" style={{ color: meta.ink }}>
                {model.title}
              </h1>
              <p className="hi text-body-lg" lang="hi" style={{ color: meta.ink }}>
                {model.hindiTitle}
              </p>
            </div>
          </div>
          {showCategory && (
            <p className="mt-3 inline-flex flex-wrap items-center gap-1.5 rounded-chip bg-white/80 px-3 py-1.5 text-body-sm font-semibold text-ink">
              <Icon name="category" size={16} /> {label(SCAM_CATEGORY, model.category)}
              <span className="hi font-normal text-ink-2" lang="hi">· {hindiLabel(SCAM_CATEGORY, model.category)}</span>
            </p>
          )}
          {model.summary && <p className="mt-3 max-w-2xl text-body-md text-ink">{model.summary}</p>}
          {model.hindiSummary && (
            <p className="hi mt-2 max-w-2xl text-body-md text-ink-2" lang="hi">
              {model.hindiSummary}
            </p>
          )}
        </div>
        {typeof model.score === 'number' && (
          <div className="flex shrink-0 justify-center rounded-card bg-white/70 p-4">
            <RiskGauge value={model.score} level={model.level} caption={model.scoreLabel} />
          </div>
        )}
      </div>
      {model.level === 'HIGH' && (
        <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-white/60 pt-4">
          <p className="text-body-sm font-semibold text-risk-high-ink">Do not reply, click, pay or share any OTP.</p>
          <a href="tel:1930" className="ml-auto inline-flex h-10 items-center gap-1.5 rounded-chip bg-risk-high-ink px-4 text-body-sm font-semibold text-white">
            <Icon name="call" size={18} /> Lost money? Call 1930
          </a>
        </div>
      )}
    </motion.section>
  )
}

export function ResultView({ model }) {
  const [exposure, setExposure] = useState('RECEIVED_ONLY')
  const linkCards = model.kind === 'url' ? model.urlAnalyses : model.urlAnalyses.slice(0, 3)
  return (
    <div className="mx-auto max-w-[1280px] px-4 py-6 md:px-8 md:py-8">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <ButtonLink to={`/check?mode=${model.kind === 'url' ? 'link' : model.kind}`} variant="ghost" size="sm" icon="arrow_back">
          Check something else
        </ButtonLink>
        <p className="text-body-sm text-ink-3">This result is kept only until you close or refresh the page.</p>
      </div>
      <VerdictHero model={model} />
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_380px]">
        <div className="min-w-0 space-y-5">
          {model.kind !== 'url' && model.kind !== 'identifier' && <HighlightedInput text={model.inputText} redFlags={model.redFlags} />}
          {model.kind === 'identifier' && <IdentifierFacts result={model.raw} />}
          {model.kind === 'email' && <EmailEvidence result={model.raw} />}
          {model.kind === 'qr' && model.raw.upi_id && (
            <Card className="p-5">
              <p className="text-label-ui uppercase text-ink-3">This QR pays to</p>
              <p className="mt-1 break-all font-mono text-title-md text-ink">{model.raw.upi_id}</p>
              <p className="mt-1 text-body-sm text-ink-2">Scanning a QR always sends money. You never need to scan to receive money.</p>
            </Card>
          )}
          {linkCards.map((analysis) => (
            <UrlAnalysisCard key={analysis.original_url} analysis={analysis} compact={model.kind !== 'url'} />
          ))}
          <RedFlagList redFlags={model.redFlags} tactics={model.tactics} />
          <ActionSteps actions={model.actions} />
          <Limitations items={model.limitations} source={model.source} notice={model.notice} />
        </div>
        <aside className="min-w-0 space-y-4">
          <ExposurePicker value={exposure} onChange={setExposure} />
          <SafeNextStep model={model} exposure={exposure} />
          <ExplainSimply key={exposure} model={model} exposure={exposure} />
          <ReportToPolice model={model} />
          <SaveEvidence model={model} />
        </aside>
      </div>
    </div>
  )
}

export function ResultPage() {
  const { entry } = useResult()
  const model = normaliseResult(entry)
  if (!model) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12">
        <Card className="p-2">
          <EmptyBlock
            icon="manage_search"
            title="No result to show"
            action={<ButtonLink to="/check" icon="search">Check something</ButtonLink>}
          >
            Results are never saved, so they disappear when the page is refreshed. Check the message again to see its result.
          </EmptyBlock>
        </Card>
      </div>
    )
  }
  return <ResultView model={model} />
}

export default ResultPage
