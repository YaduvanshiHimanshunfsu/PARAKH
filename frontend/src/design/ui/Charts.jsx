import { useState } from 'react'

// Chart steps for the risk tri-signal. Validated with the dataviz palette
// checker (light mode: all checks pass; amber is below 3:1 on white, so every
// chart using it ships a table view). Text never uses these; it uses -ink.
export const CHART_RISK = { HIGH: '#dc2626', MEDIUM: '#f59e0b', LOW: '#059669' }

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
            const gap = segments.filter((item) => item.value > 0).length > 1 ? 2 : 0
            const dash = Math.max(0, length - gap)
            const element = (
              <circle
                key={segment.label}
                cx="70"
                cy="70"
                r={radius}
                fill="none"
                stroke={segment.color}
                strokeWidth="18"
                strokeDasharray={`${dash} ${circumference - dash}`}
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

/** Horizontal magnitude bars with labels (category mix). rows: [{label, value}] */
export function BarList({ rows = [], label, color = 'var(--color-primary)' }) {
  const max = Math.max(1, ...rows.map((row) => row.value))
  return (
    <ul aria-label={label} className="space-y-2.5">
      {rows.map((row) => (
        <li key={row.label} className="grid grid-cols-[7rem_1fr_3rem] items-center gap-3 text-body-sm">
          <span className="truncate text-ink-2">{row.label}</span>
          <span className="h-2.5 rounded-r bg-canvas">
            <span className="block h-full rounded-r" style={{ width: `${(row.value / max) * 100}%`, minWidth: row.value ? 4 : 0, background: color }} />
          </span>
          <span className="text-right font-semibold text-ink tnum">{row.value}</span>
        </li>
      ))}
    </ul>
  )
}

function topRoundedPath(x, y, w, h, r) {
  return `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h} Z`
}

/**
 * Stacked daily bars with legend, hover tooltip and a table view.
 *   series: [{key, label, color}] bottom to top
 *   data:   [{date: 'YYYY-MM-DD', [key]: number}]
 */
export function StackedBars({ series, data, label, height = 200, formatDate = (d) => d.slice(5) }) {
  const [hover, setHover] = useState(null)
  const [table, setTable] = useState(false)
  const width = 720
  const pad = { top: 8, right: 8, bottom: 22, left: 32 }
  const plotW = width - pad.left - pad.right
  const plotH = height - pad.top - pad.bottom
  const totals = data.map((row) => series.reduce((sum, s) => sum + (row[s.key] || 0), 0))
  const rawMax = Math.max(1, ...totals)
  const step = rawMax <= 5 ? 1 : Math.ceil(rawMax / 4)
  const max = Math.ceil(rawMax / step) * step
  const ticks = Array.from({ length: max / step + 1 }, (_, i) => i * step)
  const col = plotW / Math.max(1, data.length)
  const barW = Math.max(2, Math.min(24, col - 3))
  const y = (value) => pad.top + plotH - (value / max) * plotH
  const labelEvery = Math.ceil(data.length / 8)
  const legend = [...series].reverse()

  return (
    <figure className="m-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <ul className="flex flex-wrap gap-3 text-body-sm text-ink-2" aria-label="Legend">
          {legend.map((s) => (
            <li key={s.key} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} /> {s.label}
            </li>
          ))}
        </ul>
        <button type="button" onClick={() => setTable(!table)} className="text-body-sm font-semibold text-primary hover:underline" aria-pressed={table}>
          {table ? 'Show chart' : 'Show table'}
        </button>
      </div>
      {table ? (
        <div className="mt-3 max-h-[260px] overflow-auto">
          <table className="w-full text-body-sm">
            <caption className="sr-only">{label}</caption>
            <thead className="sticky top-0 bg-card text-left text-ink-3">
              <tr>
                <th className="py-1 pr-3 font-semibold">Date</th>
                {series.map((s) => (
                  <th key={s.key} className="py-1 pr-3 text-right font-semibold">{s.label}</th>
                ))}
                <th className="py-1 text-right font-semibold">Total</th>
              </tr>
            </thead>
            <tbody className="tnum">
              {data.map((row, i) => (
                <tr key={row.date} className="border-t border-line-soft">
                  <td className="py-1 pr-3 text-ink-2">{row.date}</td>
                  {series.map((s) => (
                    <td key={s.key} className="py-1 pr-3 text-right text-ink">{row[s.key] || 0}</td>
                  ))}
                  <td className="py-1 text-right font-semibold text-ink">{totals[i]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="relative mt-3">
          <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img" aria-label={label} onMouseLeave={() => setHover(null)}>
            {ticks.map((tick) => (
              <g key={tick}>
                <line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} stroke="#e2e8f0" strokeWidth="1" />
                <text x={pad.left - 6} y={y(tick) + 4} textAnchor="end" fontSize="11" fill="#64748b">{tick}</text>
              </g>
            ))}
            {data.map((row, i) => {
              const x = pad.left + i * col + (col - barW) / 2
              const visible = series.filter((s) => (row[s.key] || 0) > 0)
              let base = 0
              return (
                <g key={row.date} opacity={hover === null || hover === i ? 1 : 0.45}>
                  {visible.map((s, index) => {
                    const value = row[s.key]
                    const top = y(base + value)
                    const bottom = y(base)
                    base += value
                    const isTop = index === visible.length - 1
                    // 2px surface gap between stacked segments.
                    const segY = top + (isTop ? 0 : 2)
                    const h = Math.max(1, bottom - segY)
                    const r = isTop ? Math.min(4, barW / 2, h) : 0
                    return r > 0 ? (
                      <path key={s.key} fill={s.color} d={topRoundedPath(x, segY, barW, h, r)} />
                    ) : (
                      <rect key={s.key} x={x} y={segY} width={barW} height={h} fill={s.color} />
                    )
                  })}
                  {i % labelEvery === 0 && (
                    <text x={x + barW / 2} y={height - 6} textAnchor="middle" fontSize="11" fill="#64748b">{formatDate(row.date)}</text>
                  )}
                  <rect
                    x={pad.left + i * col}
                    y={pad.top}
                    width={col}
                    height={plotH}
                    fill="transparent"
                    tabIndex={0}
                    onMouseEnter={() => setHover(i)}
                    onFocus={() => setHover(i)}
                    onBlur={() => setHover(null)}
                    aria-label={`${row.date}: ${series.map((s) => `${s.label} ${row[s.key] || 0}`).join(', ')}`}
                  />
                </g>
              )
            })}
            <line x1={pad.left} x2={width - pad.right} y1={y(0)} y2={y(0)} stroke="#94a3b8" strokeWidth="1" />
          </svg>
          {hover !== null && data[hover] && (
            <div
              role="tooltip"
              className="pointer-events-none absolute top-0 z-10 min-w-[150px] -translate-x-1/2 rounded-chip border border-line bg-card px-3 py-2 text-body-sm shadow-l3"
              style={{ left: `${Math.min(85, Math.max(15, ((pad.left + (hover + 0.5) * col) / width) * 100))}%` }}
            >
              <p className="font-semibold text-ink tnum">{data[hover].date}</p>
              {legend.map((s) => (
                <p key={s.key} className="flex items-center gap-2 text-ink-2">
                  <span className="h-2 w-2 rounded-sm" style={{ background: s.color }} /> {s.label}
                  <span className="ml-auto font-semibold text-ink tnum">{data[hover][s.key] || 0}</span>
                </p>
              ))}
              <p className="mt-1 flex border-t border-line-soft pt-1 text-ink-2">
                Total <span className="ml-auto font-semibold text-ink tnum">{totals[hover]}</span>
              </p>
            </div>
          )}
        </div>
      )}
    </figure>
  )
}
