import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card, EmptyBlock, ErrorBlock, Icon, IdentifierChip, LoadingBlock, Segmented } from '../../design/ui'
import { IDENTIFIER_META } from '../../design/vocab'
import { officerApi } from '../../lib/api'
import { PageHeader, formatDateTime, timeAgo } from './shared'

// Built from design/stitch/parakh_heat_list_hot_identifiers_registry.
// GET /investigate/heatlist ranks identifiers by how many cases mention them.
// Trend = cases in the last 7 days vs the 7 days before (previous_case_count).

const TYPES = ['UPI', 'PHONE', 'DOMAIN', 'URL', 'BANK_ACCOUNT', 'EMAIL', 'TELEGRAM', 'IP', 'PACKAGE', 'CERT_SHA256']
const PERIODS = [
  { value: '', label: 'All time' },
  { value: '30', label: '30 days' },
  { value: '7', label: '7 days' },
]

export function trend(recent, previous) {
  if (recent === 0 && previous === 0) return { label: 'Quiet', icon: 'remove', tone: 'text-ink-3' }
  if (previous === 0) return { label: 'New this week', icon: 'fiber_new', tone: 'text-risk-high-ink' }
  const change = Math.round(((recent - previous) / previous) * 100)
  if (change > 0) return { label: `+${change}% vs last week`, icon: 'trending_up', tone: 'text-risk-high-ink' }
  if (change < 0) return { label: `${change}% vs last week`, icon: 'trending_down', tone: 'text-risk-low-ink' }
  return { label: 'Same as last week', icon: 'trending_flat', tone: 'text-ink-2' }
}

export function HeatlistPage() {
  const [params, setParams] = useSearchParams()
  const type = params.get('type') || ''
  const days = params.get('days') || ''
  const list = useQuery({
    queryKey: ['heatlist', type, days],
    queryFn: () => officerApi.heatlist({ type: type || undefined, days: days || undefined, limit: 50 }),
  })

  function set(key, value) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  const rows = list.data || []
  const max = Math.max(1, ...rows.map((row) => row.case_count))

  return (
    <div>
      <PageHeader title="Heat-list" hindi="सबसे अधिक रिपोर्ट किए गए पहचानकर्ता" eyebrow="Hot identifiers">
        <Segmented label="Period" size="sm" value={days} onChange={(value) => set('days', value)} options={PERIODS} />
      </PageHeader>

      <div className="mb-4 flex flex-wrap gap-1.5" role="group" aria-label="Identifier type">
        <button type="button" aria-pressed={!type} onClick={() => set('type', '')} className={`rounded-chip border px-3 py-1.5 text-body-sm font-semibold ${!type ? 'border-primary bg-primary text-white' : 'border-line bg-card text-ink-2 hover:text-primary'}`}>
          All types
        </button>
        {TYPES.map((key) => (
          <button key={key} type="button" aria-pressed={type === key} onClick={() => set('type', key)} className={`inline-flex items-center gap-1 rounded-chip border px-3 py-1.5 text-body-sm font-semibold ${type === key ? 'border-primary bg-primary text-white' : 'border-line bg-card text-ink-2 hover:text-primary'}`}>
            <Icon name={IDENTIFIER_META[key].icon} size={16} /> {IDENTIFIER_META[key].label}
          </button>
        ))}
      </div>

      <Card className="overflow-hidden">
        {list.isPending && <div className="p-4"><LoadingBlock rows={6} /></div>}
        {list.isError && <ErrorBlock error={list.error} onRetry={() => list.refetch()} />}
        {list.data && rows.length === 0 && (
          <EmptyBlock icon="local_fire_department" title="No identifiers yet">Identifiers appear here once cases mention them.</EmptyBlock>
        )}
        {rows.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-body-sm">
              <caption className="sr-only">Identifiers ranked by number of cases</caption>
              <thead className="bg-canvas text-left text-label-ui uppercase text-ink-3">
                <tr>
                  <th className="px-4 py-3">#</th>
                  <th className="px-4 py-3">Identifier</th>
                  <th className="px-4 py-3">Cases</th>
                  <th className="px-4 py-3">Last 7 days</th>
                  <th className="px-4 py-3">Trend</th>
                  <th className="px-4 py-3">First / last seen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {rows.map((row, index) => {
                  const t = trend(row.recent_case_count, row.previous_case_count)
                  return (
                    <tr key={`${row.type}:${row.value}`} className="hover:bg-canvas">
                      <td className="px-4 py-3 text-ink-3 tnum">{index + 1}</td>
                      <td className="px-4 py-3">
                        <IdentifierChip type={row.type} value={row.value} to={`/investigate/identifier/${row.type}/${encodeURIComponent(row.value)}`} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="h-2 w-24 rounded-r bg-canvas">
                            <span className="block h-full rounded-r bg-primary" style={{ width: `${(row.case_count / max) * 100}%` }} />
                          </span>
                          <span className="font-semibold text-ink tnum">{row.case_count}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-ink tnum">
                        {row.recent_case_count} <span className="text-ink-3">(prev. {row.previous_case_count})</span>
                      </td>
                      <td className={`px-4 py-3 ${t.tone}`}>
                        <span className="inline-flex items-center gap-1 font-semibold"><Icon name={t.icon} size={18} /> {t.label}</span>
                      </td>
                      <td className="px-4 py-3 text-ink-2" title={`${formatDateTime(row.first_seen)} → ${formatDateTime(row.last_seen)}`}>
                        {timeAgo(row.first_seen)} / {timeAgo(row.last_seen)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <p className="mt-3 text-body-sm text-ink-3">
        A high count means many reports mention it, not that its owner is guilty. Confirm with the bank or telecom provider before action. <Link to="/investigate/cases" className="font-semibold text-primary hover:underline">Search cases</Link>
      </p>
    </div>
  )
}

export default HeatlistPage
