import { Link } from 'react-router-dom'

// Shared presentation for the officer console. Colour is never the only signal:
// every risk and severity badge also carries its label as text.

const RISK_STYLES = {
  HIGH: 'bg-red-100 text-red-900 ring-red-300',
  MEDIUM: 'bg-amber-100 text-amber-900 ring-amber-300',
  LOW: 'bg-emerald-100 text-emerald-900 ring-emerald-300',
}

const SEVERITY_STYLES = {
  HIGH: 'bg-red-600 text-white',
  MEDIUM: 'bg-amber-500 text-white',
  LOW: 'bg-slate-500 text-white',
}

const STATUS_STYLES = {
  NEW: 'bg-blue-100 text-blue-900 ring-blue-300',
  UNDER_REVIEW: 'bg-violet-100 text-violet-900 ring-violet-300',
  CLOSED: 'bg-slate-200 text-slate-700 ring-slate-300',
}

const ARTIFACT_LABELS = {
  MESSAGE: 'Message',
  URL: 'URL',
  EMAIL: 'Email',
  APK: 'Android app',
  WEBSITE: 'Website',
}

export function RiskBadge({ level, score }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-bold ring-1 ${RISK_STYLES[level] || RISK_STYLES.LOW}`}
    >
      {level}
      {score !== undefined && <span className="font-semibold opacity-75">{score}/100</span>}
    </span>
  )
}

export function SeverityTag({ severity }) {
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${SEVERITY_STYLES[severity] || SEVERITY_STYLES.LOW}`}
    >
      {severity}
    </span>
  )
}

export function StatusBadge({ status }) {
  return (
    <span
      className={`inline-block rounded-lg px-2 py-0.5 text-[11px] font-semibold ring-1 ${STATUS_STYLES[status] || STATUS_STYLES.NEW}`}
    >
      {status.replace('_', ' ')}
    </span>
  )
}

export function ArtifactTag({ type }) {
  return (
    <span className="inline-block rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
      {ARTIFACT_LABELS[type] || type}
    </span>
  )
}

export function IdentifierChip({ type, value }) {
  return (
    <Link
      to={`/investigate/identifier/${encodeURIComponent(type)}/${encodeURIComponent(value)}`}
      className="group inline-flex max-w-full items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs transition hover:border-blue-400 hover:bg-blue-50"
      title={`See every case containing ${value}`}
    >
      <span className="font-semibold text-slate-500 group-hover:text-blue-700">{type}</span>
      <span className="truncate font-mono text-slate-900">{value}</span>
    </Link>
  )
}

export function Panel({ title, action, children, muted }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-bold text-slate-900">{title}</h2>
        {action}
      </header>
      <div className={`px-4 py-3 ${muted ? 'text-sm text-slate-500' : ''}`}>{children}</div>
    </section>
  )
}

export function EmptyState({ children }) {
  return <p className="py-6 text-center text-sm italic text-slate-400">{children}</p>
}

export function ErrorNote({ message }) {
  if (!message) return null
  return (
    <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-red-800 ring-1 ring-red-200">
      {message}
    </p>
  )
}

export function formatWhen(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
