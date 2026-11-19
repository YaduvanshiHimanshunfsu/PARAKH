import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Download, Search } from 'lucide-react'
import * as api from '../../lib/investigateApi'
import {
  ArtifactTag,
  EmptyState,
  ErrorNote,
  RiskBadge,
  StatusBadge,
  formatWhen,
} from '../../features/investigate/ui'

const PAGE_SIZE = 25

const ARTIFACT_OPTIONS = [
  ['', 'All types'],
  ['MESSAGE', 'Message'],
  ['URL', 'URL'],
  ['EMAIL', 'Email'],
  ['APK', 'Android app'],
  ['WEBSITE', 'Website'],
]
const RISK_OPTIONS = [['', 'All risk'], ['HIGH', 'High'], ['MEDIUM', 'Medium'], ['LOW', 'Low']]
const STATUS_OPTIONS = [
  ['', 'All statuses'],
  ['NEW', 'New'],
  ['UNDER_REVIEW', 'Under review'],
  ['CLOSED', 'Closed'],
]

export function CaseListPage() {
  const [filters, setFilters] = useState({ q: '', artifact_type: '', risk_level: '', status: '' })
  const [pending, setPending] = useState('')
  const [offset, setOffset] = useState(0)
  const [result, setResult] = useState({ total: 0, cases: [] })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setResult(await api.searchCases({ ...filters, limit: PAGE_SIZE, offset }))
    } catch (caught) {
      setError(caught.message)
    } finally {
      setLoading(false)
    }
  }, [filters, offset])

  useEffect(() => {
    load()
  }, [load])

  function applySearch(event) {
    event.preventDefault()
    setOffset(0)
    setFilters((current) => ({ ...current, q: pending.trim() }))
  }

  function setFilter(key, value) {
    setOffset(0)
    setFilters((current) => ({ ...current, [key]: value }))
  }

  async function exportCsv(kind) {
    try {
      const download = kind === 'cases' ? api.downloadCasesCsv : api.downloadIdentifiersCsv
      await download(filters)
    } catch (caught) {
      setError(caught.message)
    }
  }

  const shown = result.cases.length
  const from = result.total === 0 ? 0 : offset + 1

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Case history</h1>
          <p className="text-sm text-slate-500">
            Search messages, apps and websites by content or by any extracted identifier.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => exportCsv('cases')}
            className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <Download size={14} /> Cases CSV
          </button>
          <button
            type="button"
            onClick={() => exportCsv('identifiers')}
            className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <Download size={14} /> Identifiers CSV
          </button>
        </div>
      </div>

      <form onSubmit={applySearch} className="flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-3">
        <div className="flex min-w-[240px] flex-1 items-center gap-2 rounded-lg border border-slate-300 px-3">
          <Search size={15} className="text-slate-400" />
          <input
            value={pending}
            onChange={(event) => setPending(event.target.value)}
            placeholder="Phone, UPI ID, domain, package, case ID, or text…"
            aria-label="Search cases"
            className="w-full py-2 text-sm outline-none"
          />
        </div>
        {[
          ['artifact_type', ARTIFACT_OPTIONS],
          ['risk_level', RISK_OPTIONS],
          ['status', STATUS_OPTIONS],
        ].map(([key, options]) => (
          <select
            key={key}
            value={filters[key]}
            onChange={(event) => setFilter(key, event.target.value)}
            aria-label={key.replace('_', ' ')}
            className="rounded-lg border border-slate-300 px-2.5 py-2 text-sm outline-none focus:border-blue-500"
          >
            {options.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        ))}
        <button
          type="submit"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700"
        >
          Search
        </button>
      </form>

      <ErrorNote message={error} />

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2.5 text-left font-bold">Case</th>
              <th className="px-4 py-2.5 text-left font-bold">Type</th>
              <th className="px-4 py-2.5 text-left font-bold">Risk</th>
              <th className="px-4 py-2.5 text-left font-bold">Summary</th>
              <th className="px-4 py-2.5 text-left font-bold">Signals</th>
              <th className="px-4 py-2.5 text-left font-bold">Status</th>
              <th className="px-4 py-2.5 text-left font-bold">Opened</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                  Loading cases…
                </td>
              </tr>
            )}
            {!loading && shown === 0 && (
              <tr>
                <td colSpan={7}>
                  <EmptyState>
                    No cases match these filters. Submit a message, app, or website to begin.
                  </EmptyState>
                </td>
              </tr>
            )}
            {!loading &&
              result.cases.map((row) => (
                <tr key={row.case_id} className="border-t border-slate-100 align-top hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/investigate/case/${row.case_id}`}
                      className="font-mono text-xs font-bold text-blue-700 hover:underline"
                    >
                      {row.case_id}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <ArtifactTag type={row.artifact_type} />
                  </td>
                  <td className="px-4 py-3">
                    <RiskBadge level={row.risk_level} score={row.risk_score} />
                  </td>
                  <td className="max-w-sm px-4 py-3">
                    <p className="font-medium text-slate-800">{row.summary}</p>
                    {row.preview && (
                      <p className="mt-0.5 line-clamp-2 text-xs text-slate-500">{row.preview}</p>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-600">
                    {row.finding_count} indicators
                    <br />
                    {row.identifier_count} identifiers
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={row.status} />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                    {formatWhen(row.created_at)}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {result.total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500">
            Showing {from}–{offset + shown} of {result.total}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={offset + shown >= result.total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
