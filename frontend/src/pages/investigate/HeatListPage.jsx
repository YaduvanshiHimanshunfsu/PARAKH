import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'
import * as api from '../../lib/investigateApi'
import { EmptyState, ErrorNote, formatWhen } from '../../features/investigate/ui'

const TYPES = [
  ['', 'All'],
  ['PHONE', 'Phone'],
  ['UPI', 'UPI'],
  ['DOMAIN', 'Domain'],
  ['PACKAGE', 'App package'],
  ['BANK_ACCOUNT', 'Bank account'],
  ['CRYPTO_ETH', 'Crypto'],
  ['TELEGRAM', 'Telegram'],
  ['IP', 'IP address'],
]

const WINDOWS = [
  ['', 'All time'],
  ['7', 'Last 7 days'],
  ['30', 'Last 30 days'],
]

export function HeatListPage() {
  const [type, setType] = useState('')
  const [days, setDays] = useState('')
  const [entries, setEntries] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setEntries(await api.getHeatList({ type, days, limit: 50 }))
    } catch (caught) {
      setError(caught.message)
    } finally {
      setLoading(false)
    }
  }, [type, days])

  useEffect(() => {
    load()
  }, [load])

  const peak = Math.max(1, ...entries.map((entry) => entry.case_count))

  return (
    <div className="space-y-4">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-bold text-slate-900">
          <TrendingUp size={20} className="text-red-600" /> Heat-list
        </h1>
        <p className="text-sm text-slate-500">
          The identifiers appearing in the most cases. A number or account reused across many
          reports is usually one operation.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-3">
        <select
          value={type}
          onChange={(event) => setType(event.target.value)}
          aria-label="Identifier type"
          className="rounded-lg border border-slate-300 px-2.5 py-2 text-sm"
        >
          {TYPES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={days}
          onChange={(event) => setDays(event.target.value)}
          aria-label="Time window"
          className="rounded-lg border border-slate-300 px-2.5 py-2 text-sm"
        >
          {WINDOWS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <ErrorNote message={error} />

      {loading ? (
        <p className="py-10 text-center text-sm text-slate-500">Loading…</p>
      ) : entries.length === 0 ? (
        <EmptyState>No identifiers recorded yet. Analyse some items to build the heat-list.</EmptyState>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2.5 text-left font-bold">#</th>
                <th className="px-4 py-2.5 text-left font-bold">Type</th>
                <th className="px-4 py-2.5 text-left font-bold">Identifier</th>
                <th className="px-4 py-2.5 text-left font-bold">Cases</th>
                <th className="px-4 py-2.5 text-left font-bold">Last 7 days</th>
                <th className="px-4 py-2.5 text-left font-bold">First seen</th>
                <th className="px-4 py-2.5 text-left font-bold">Last seen</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, index) => (
                <tr key={`${entry.type}-${entry.value}`} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-2.5 text-xs font-bold text-slate-400">{index + 1}</td>
                  <td className="px-4 py-2.5">
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-700">
                      {entry.type}
                    </span>
                  </td>
                  <td className="max-w-xs px-4 py-2.5">
                    <Link
                      to={`/investigate/identifier/${encodeURIComponent(entry.type)}/${encodeURIComponent(entry.value)}`}
                      className="break-all font-mono text-xs text-blue-700 hover:underline"
                    >
                      {entry.value}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="w-7 text-sm font-bold text-slate-900">{entry.case_count}</span>
                      <span className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-100">
                        <span
                          className="block h-full rounded-full bg-red-500"
                          style={{ width: `${(entry.case_count / peak) * 100}%` }}
                        />
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-xs">
                    {entry.recent_case_count > 0 ? (
                      <span className="font-bold text-red-700">+{entry.recent_case_count}</span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2.5 text-xs text-slate-500">
                    {formatWhen(entry.first_seen)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2.5 text-xs text-slate-500">
                    {formatWhen(entry.last_seen)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
