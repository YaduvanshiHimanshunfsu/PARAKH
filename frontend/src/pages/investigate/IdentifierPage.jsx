import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import * as api from '../../lib/investigateApi'
import {
  ArtifactTag,
  EmptyState,
  ErrorNote,
  RiskBadge,
  StatusBadge,
  formatWhen,
} from '../../features/investigate/ui'

export function IdentifierPage() {
  const { type, value } = useParams()
  const decoded = decodeURIComponent(value || '')
  const [cases, setCases] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api
      .getIdentifierCases(type, decoded)
      .then((result) => {
        if (!cancelled) setCases(result.cases || [])
      })
      .catch((caught) => {
        if (!cancelled) setError(caught.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [type, decoded])

  const artifactTypes = [...new Set(cases.map((row) => row.artifact_type))]

  return (
    <div className="space-y-4">
      <Link
        to="/investigate"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-blue-700"
      >
        <ArrowLeft size={15} /> Back to cases
      </Link>

      <header className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{type}</p>
        <h1 className="break-all font-mono text-lg font-bold text-slate-900">{decoded}</h1>
        <p className="mt-1 text-sm text-slate-600">
          Appears in <strong>{cases.length}</strong> case{cases.length === 1 ? '' : 's'}
          {artifactTypes.length > 1 && (
            <> across <strong>{artifactTypes.length}</strong> artifact types — a reused identifier
            linking separate reports.</>
          )}
        </p>
      </header>

      <ErrorNote message={error} />

      {loading ? (
        <p className="py-10 text-center text-sm text-slate-500">Loading…</p>
      ) : cases.length === 0 ? (
        <EmptyState>No cases contain this identifier.</EmptyState>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2.5 text-left font-bold">Case</th>
                <th className="px-4 py-2.5 text-left font-bold">Type</th>
                <th className="px-4 py-2.5 text-left font-bold">Risk</th>
                <th className="px-4 py-2.5 text-left font-bold">Summary</th>
                <th className="px-4 py-2.5 text-left font-bold">Status</th>
                <th className="px-4 py-2.5 text-left font-bold">Opened</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((row) => (
                <tr key={row.case_id} className="border-t border-slate-100 hover:bg-slate-50">
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
                  <td className="max-w-md px-4 py-3 text-slate-800">{row.summary}</td>
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
      )}
    </div>
  )
}
