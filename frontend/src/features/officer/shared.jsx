import { Link } from 'react-router-dom'
import { Icon, RiskBadge } from '../../design/ui'

// Small pieces shared by the officer screens.

export const ARTIFACT_META = {
  MESSAGE: { label: 'Message', icon: 'sms' },
  URL: { label: 'Link', icon: 'link' },
  EMAIL: { label: 'Email', icon: 'mail' },
  APK: { label: 'APK', icon: 'android' },
  WEBSITE: { label: 'Website', icon: 'language' },
}

export const STATUS_META = {
  NEW: { label: 'New', className: 'bg-primary-tint text-primary' },
  UNDER_REVIEW: { label: 'Under review', className: 'bg-risk-medium-bg text-risk-medium-ink' },
  CLOSED: { label: 'Closed', className: 'bg-canvas text-ink-2' },
}

export const SOURCE_META = {
  OFFICER: { label: 'Officer', icon: 'badge' },
  CITIZEN: { label: 'Citizen', icon: 'person' },
}

export function ArtifactTag({ type }) {
  const meta = ARTIFACT_META[type] || { label: type, icon: 'description' }
  return (
    <span className="inline-flex items-center gap-1 text-body-sm text-ink-2">
      <Icon name={meta.icon} size={16} /> {meta.label}
    </span>
  )
}

export function StatusPill({ status }) {
  const meta = STATUS_META[status] || { label: status, className: 'bg-canvas text-ink-2' }
  return <span className={`inline-flex rounded-chip px-2 py-0.5 text-label-ui uppercase ${meta.className}`}>{meta.label}</span>
}

export function SourceTag({ source }) {
  const meta = SOURCE_META[source] || { label: source, icon: 'help' }
  return (
    <span className="inline-flex items-center gap-1 text-body-sm text-ink-3">
      <Icon name={meta.icon} size={15} /> {meta.label}
    </span>
  )
}

const RTF = typeof Intl !== 'undefined' && Intl.RelativeTimeFormat ? new Intl.RelativeTimeFormat('en-IN', { numeric: 'auto' }) : null

export function timeAgo(iso, now = Date.now()) {
  if (!iso) return '—'
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000)
  const abs = Math.abs(seconds)
  if (!RTF) return new Date(iso).toLocaleString('en-IN')
  if (abs < 60) return RTF.format(seconds, 'second')
  if (abs < 3600) return RTF.format(Math.round(seconds / 60), 'minute')
  if (abs < 86400) return RTF.format(Math.round(seconds / 3600), 'hour')
  return RTF.format(Math.round(seconds / 86400), 'day')
}

export function formatDateTime(iso) {
  return iso ? new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'
}

/** One case row for tables and lists. */
export function CaseLink({ summary, compact = false }) {
  return (
    <Link to={`/investigate/case/${encodeURIComponent(summary.case_id)}`} className="group flex items-start gap-3 rounded-chip p-2 hover:bg-canvas">
      <RiskBadge level={summary.risk_level} score={compact ? undefined : summary.risk_score} className="mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-x-2 font-mono text-body-sm font-semibold text-ink group-hover:text-primary">
          {summary.case_id}
          <ArtifactTag type={summary.artifact_type} />
        </p>
        <p className="truncate text-body-sm text-ink-2">{summary.preview || summary.summary}</p>
      </div>
      <span className="shrink-0 text-body-sm text-ink-3">{timeAgo(summary.created_at)}</span>
    </Link>
  )
}

/** Save a fetch Response (CSV/JSON export) as a file. */
export async function saveResponse(response, fallbackName) {
  const disposition = response.headers.get('Content-Disposition') || ''
  const match = /filename="?([^";]+)"?/i.exec(disposition)
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = match?.[1] || fallbackName
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** Open an HTML report Response in a new tab. */
export async function openHtmlResponse(response) {
  const blob = new Blob([await response.text()], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const opened = window.open(url, '_blank', 'noopener')
  if (!opened) {
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.target = '_blank'
    anchor.rel = 'noopener'
    anchor.click()
  }
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

export function PageHeader({ eyebrow, title, hindi, children }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        {eyebrow && <p className="text-label-ui uppercase text-accent-strong">{eyebrow}</p>}
        <h1 className="text-headline-lg-mobile md:text-headline-lg">{title}</h1>
        {hindi && <p className="hi text-body-md text-ink-2" lang="hi">{hindi}</p>}
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  )
}
