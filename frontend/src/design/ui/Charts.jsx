// Small SVG charts for KPIs and dashboards. No chart library: these match the
// Stitch look, stay light, and render offline. Every chart has a text
// alternative because a chart alone is not accessible.

export function Sparkline({ values = [], color = 'var(--color-primary)', width = 96, height = 28, label }) {
  if (values.length < 2) return null
  const max = Math.max(...values)
  const min = Math.min(...values)
  const span = max - min || 1
  const step = width / (values.length - 1)
  const points = values.map((v, i) => `${(i * step).toFixed(1)},${(height - 2 - ((v - min) / span) * (height - 4)).toFixed(1)}`)
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label || `Trend: ${values.join(', ')}`}>
      <polyline points={points.join(' ')} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

/** KPI tile. `value` must come from the API — pass null while loading. */
export function KpiCard({ label, hindi, value, delta, trend, tone = 'default', icon }) {
  const toneClass = { default: 'text-ink', high: 'text-risk-high-ink', primary: 'text-primary', medium: 'text-risk-medium-ink' }
  return (
    <div className="rounded-card border border-line bg-card p-4 shadow-l1">
      <div className="flex items-start justify-between gap-2">
        <p className="text-label-ui uppercase text-ink-2">
          {label}
          {hindi && (
            <span className="hi ml-1 normal-case text-ink-3" lang="hi">
              ({hindi})
            </span>
          )}
        </p>
        {icon}
      </div>
      <p className={`mt-2 text-headline-lg tnum ${toneClass[tone] || toneClass.default}`}>{value ?? '—'}</p>
      <div className="mt-1 flex items-center justify-between gap-2">
        {delta ? <span className="text-body-sm text-ink-2">{delta}</span> : <span />}
        {trend && <Sparkline values={trend} />}
      </div>
    </div>
  )
}

/** Donut with a legend. segments: [{label, value, color}] */
export function Donut({ segments = [], size = 140, label, centerLabel }) {
  const total = segments.reduce((sum, s) => sum + (s.value || 0), 0)
  const radius = 52
  const circumference = 2 * Math.PI * radius
  let offset = 0
  return (
    <div className="flex flex-wrap items-center gap-4">
      <svg width={size} height={size} viewBox="0 0 140 140" role="img" aria-label={label || 'Distribution'}>
        <circle cx="70" cy="70" r={radius} fill="none" stroke="#eef2f7" strokeWidth="18" />
        {total > 0 &&
          segments.map((segment) => {
            const length = (segment.value / total) * circumference
            const element = (
              <circle
                key={segment.label}
                cx="70"
                cy="70"
                r={radius}
                fill="none"
                stroke={segment.color}
                strokeWidth="18"
                strokeDasharray={`${length} ${circumference - length}`}
                strokeDashoffset={-offset}
                transform="rotate(-90 70 70)"
              />
            )
            offset += length
            return element
          })}
        <text x="70" y="68" textAnchor="middle" fontSize="20" fontWeight="800" fill="#0f172a" className="tnum">
          {total}
        </text>
        <text x="70" y="86" textAnchor="middle" fontSize="10" fill="#475569">
          {centerLabel || 'total'}
        </text>
      </svg>
      <ul className="space-y-1 text-body-sm">
        {segments.map((segment) => (
          <li key={segment.label} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: segment.color }} />
            <span className="text-ink-2">{segment.label}</span>
            <span className="ml-auto font-semibold text-ink tnum">
              {segment.value}
              {total > 0 && <span className="ml-1 font-normal text-ink-3">({Math.round((segment.value / total) * 100)}%)</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
