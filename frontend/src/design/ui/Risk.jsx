import { motion, useReducedMotion } from 'framer-motion'
import { riskMeta, toRiskLevel } from '../vocab'
import { Icon } from './Icon'

/** Compact risk badge: tint + ink + icon + text, optional score. */
export function RiskBadge({ level, score, hindi = false, className = '' }) {
  const meta = riskMeta(level)
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-chip px-2 py-0.5 text-label-ui uppercase ${className}`}
      style={{ background: meta.bg, color: meta.ink, boxShadow: `inset 0 0 0 1px ${meta.line}33` }}
    >
      <Icon name={meta.icon} size={15} filled />
      {meta.label}
      {hindi && (
        <span className="hi normal-case" lang="hi">
          · {meta.hindi}
        </span>
      )}
      {typeof score === 'number' && <span className="tnum">· {score}</span>}
    </span>
  )
}

/** Verdict container (DESIGN.md §Components 4): tinted card with a risk border. */
export function RiskCard({ level, title, hindiTitle, children, className = '' }) {
  const meta = riskMeta(level)
  return (
    <section
      className={`rounded-card border p-5 ${className}`}
      style={{ background: meta.bg, borderColor: `color-mix(in srgb, ${meta.line} 30%, white)` }}
    >
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-white" style={{ color: meta.ink }}>
          <Icon name={meta.icon} size={24} filled />
        </span>
        <div className="min-w-0">
          <h2 className="text-headline-sm" style={{ color: meta.ink }}>
            {title}
          </h2>
          {hindiTitle && (
            <p className="hi text-body-md" lang="hi" style={{ color: meta.ink }}>
              {hindiTitle}
            </p>
          )}
          {children && <div className="mt-2 text-body-md text-ink-2">{children}</div>}
        </div>
      </div>
    </section>
  )
}

const ARC_LENGTH = Math.PI * 47 // semicircle, r = 47

/**
 * Semicircular risk gauge (0–100). The number shown is whatever the backend
 * returned (risk score or confidence) — the gauge never invents one.
 */
export function RiskGauge({ value, level, caption, size = 160 }) {
  const reduceMotion = useReducedMotion()
  const clamped = Math.max(0, Math.min(100, Number(value) || 0))
  const meta = riskMeta(level ?? (clamped >= 70 ? 'HIGH' : clamped >= 35 ? 'MEDIUM' : 'LOW'))
  const offset = ARC_LENGTH * (1 - clamped / 100)
  return (
    <figure className="m-0 flex flex-col items-center" style={{ width: size }}>
      <svg viewBox="0 0 110 62" width={size} role="img" aria-label={`${meta.label}: ${clamped} out of 100`}>
        <path d="M8 56 A47 47 0 0 1 102 56" fill="none" stroke="#e2e8f0" strokeWidth="11" strokeLinecap="round" />
        <motion.path
          d="M8 56 A47 47 0 0 1 102 56"
          fill="none"
          stroke={meta.line}
          strokeWidth="11"
          strokeLinecap="round"
          strokeDasharray={ARC_LENGTH}
          initial={{ strokeDashoffset: reduceMotion ? offset : ARC_LENGTH }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: reduceMotion ? 0 : 0.9, ease: [0.16, 1, 0.3, 1] }}
        />
        <text x="55" y="50" textAnchor="middle" className="tnum" fontSize="22" fontWeight="800" fill="#0f172a">
          {clamped}
        </text>
        <text x="55" y="60" textAnchor="middle" fontSize="7" fill="#475569">
          / 100
        </text>
      </svg>
      {caption && (
        <figcaption className="mt-1 text-label-ui uppercase" style={{ color: meta.ink }}>
          {caption}
        </figcaption>
      )}
    </figure>
  )
}

export { toRiskLevel }
