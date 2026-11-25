import { Link } from 'react-router-dom'
import { ParakhMark } from './ParakhMark'

/** PARAKH wordmark. No state emblem or police insignia (H.1). */
export function Brand({ subtitle, to = '/', compact = false }) {
  return (
    <Link to={to} className="flex min-w-0 items-center gap-2.5" aria-label="PARAKH home">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary text-white shadow-l1">
        <ParakhMark size={22} />
      </span>
      <span className="min-w-0 leading-tight">
        <span className="block text-title-md font-extrabold text-primary">
          PARAKH{' '}
          <span className="hi font-bold text-accent-strong" lang="hi">
            परख
          </span>
        </span>
        {!compact && subtitle && <span className="block truncate text-[11px] font-semibold uppercase tracking-wide text-ink-2">{subtitle}</span>}
      </span>
    </Link>
  )
}
