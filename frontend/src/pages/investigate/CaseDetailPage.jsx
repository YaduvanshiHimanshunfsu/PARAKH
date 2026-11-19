import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Copy, FileJson, Printer } from 'lucide-react'
import * as api from '../../lib/investigateApi'
import {
  ArtifactTag,
  EmptyState,
  ErrorNote,
  IdentifierChip,
  Panel,
  RiskBadge,
  SeverityTag,
  StatusBadge,
  formatWhen,
} from '../../features/investigate/ui'

const STATUSES = ['NEW', 'UNDER_REVIEW', 'CLOSED']

export function CaseDetailPage() {
  const { caseId } = useParams()
  const [detail, setDetail] = useState(null)
  const [linked, setLinked] = useState([])
  const [similar, setSimilar] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const record = await api.getCase(caseId)
      setDetail(record)
      setNote(record.officer_note || '')
      // Intelligence panels are secondary: a failure there must not blank the case.
      const [linkedResult, similarResult] = await Promise.allSettled([
        api.getLinkedCases(caseId),
        api.getSimilarCases(caseId),
      ])
      setLinked(linkedResult.status === 'fulfilled' ? linkedResult.value : [])
      setSimilar(similarResult.status === 'fulfilled' ? similarResult.value : [])
    } catch (caught) {
      setError(caught.message)
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    load()
  }, [load])

  async function save(patch) {
    setSaving(true)
    setSaved(false)
    setError('')
    try {
      setDetail(await api.updateCase(caseId, patch))
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (caught) {
      setError(caught.message)
    } finally {
      setSaving(false)
    }
  }

  async function exportReport(kind, redacted) {
    try {
      if (kind === 'html') await api.openCaseReport(caseId, redacted)
      else await api.downloadCaseJson(caseId, redacted)
    } catch (caught) {
      setError(caught.message)
    }
  }

  if (loading) return <p className="py-16 text-center text-sm text-slate-500">Loading case…</p>
  if (error && !detail) return <ErrorNote message={error} />
  if (!detail) return <ErrorNote message="Case not found." />

  const groupedIdentifiers = detail.identifiers.reduce((groups, item) => {
    ;(groups[item.type] ||= []).push(item)
    return groups
  }, {})

  return (
    <div className="space-y-4">
      <Link
        to="/investigate"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-blue-700"
      >
        <ArrowLeft size={15} /> Back to cases
      </Link>

      <ErrorNote message={error} />

      <header className="flex flex-wrap items-start justify-between gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-bold text-slate-900">{detail.case_id}</span>
            <ArtifactTag type={detail.artifact_type} />
            <StatusBadge status={detail.status} />
            <span className="text-xs text-slate-400">
              {detail.source === 'CITIZEN' ? 'Citizen report' : 'Officer submission'}
            </span>
          </div>
          <h1 className="mt-1.5 text-lg font-bold text-slate-900">{detail.summary}</h1>
          <p className="text-xs text-slate-500">Opened {formatWhen(detail.created_at)}</p>
          {detail.reporter_note && (
            <p className="mt-2 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
              <span className="font-semibold">Reporter note:</span> {detail.reporter_note}
            </p>
          )}
        </div>

        <div className="flex flex-col items-end gap-2">
          <RiskBadge level={detail.risk_level} score={detail.risk_score} />
          <div className="flex flex-wrap justify-end gap-1.5">
            <button
              type="button"
              onClick={() => exportReport('html', false)}
              className="flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700"
            >
              <Printer size={13} /> Full report
            </button>
            <button
              type="button"
              onClick={() => exportReport('html', true)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              <Printer size={13} /> Redacted
            </button>
            <button
              type="button"
              onClick={() => exportReport('json', false)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              <FileJson size={13} /> JSON
            </button>
          </div>
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Panel title={`Why this risk level (${detail.findings.length} indicators)`}>
            {detail.findings.length === 0 ? (
              <EmptyState>No indicators were recorded.</EmptyState>
            ) : (
              <ul className="space-y-2.5">
                {detail.findings.map((finding, index) => (
                  <li key={`${finding.code}-${index}`} className="flex gap-3">
                    <SeverityTag severity={finding.severity} />
                    <div className="min-w-0">
                      <p className="font-mono text-xs font-bold text-slate-900">{finding.code}</p>
                      <p className="text-sm text-slate-700">{finding.explanation}</p>
                      {finding.evidence && (
                        <p className="mt-0.5 break-words rounded bg-slate-50 px-2 py-1 font-mono text-xs text-slate-600">
                          {finding.evidence}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title={`Extracted identifiers (${detail.identifiers.length})`}>
            {detail.identifiers.length === 0 ? (
              <EmptyState>No identifiers were extracted.</EmptyState>
            ) : (
              <div className="space-y-3">
                {Object.entries(groupedIdentifiers).map(([type, items]) => (
                  <div key={type}>
                    <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-slate-500">
                      {type}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {items.map((item) => (
                        <IdentifierChip key={item.value} type={item.type} value={item.value} />
                      ))}
                    </div>
                  </div>
                ))}
                <p className="pt-1 text-xs text-slate-400">
                  Select an identifier to see every other case it appears in.
                </p>
              </div>
            )}
          </Panel>

          {detail.content_text && (
            <Panel
              title="Evidence snapshot"
              action={
                <button
                  type="button"
                  onClick={() => navigator.clipboard?.writeText(detail.content_text)}
                  className="flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-blue-700"
                >
                  <Copy size={13} /> Copy
                </button>
              }
            >
              <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-xs text-slate-800">
                {detail.content_text}
              </pre>
            </Panel>
          )}
        </div>

        <div className="space-y-4">
          <Panel title="Case status">
            <div className="space-y-3">
              <div className="flex flex-wrap gap-1.5">
                {STATUSES.map((value) => (
                  <button
                    key={value}
                    type="button"
                    disabled={saving || detail.status === value}
                    onClick={() => save({ status: value })}
                    className={`rounded-lg px-2.5 py-1.5 text-xs font-semibold transition ${
                      detail.status === value
                        ? 'bg-blue-600 text-white'
                        : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    {value.replace('_', ' ')}
                  </button>
                ))}
              </div>
              <textarea
                rows={4}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Investigation notes…"
                aria-label="Officer note"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
              />
              <button
                type="button"
                disabled={saving}
                onClick={() => save({ officer_note: note })}
                className="w-full rounded-lg bg-slate-900 py-2 text-xs font-bold text-white hover:bg-slate-700 disabled:bg-slate-300"
              >
                {saving ? 'Saving…' : saved ? 'Saved' : 'Save note'}
              </button>
            </div>
          </Panel>

          <Panel title={`Linked cases (${linked.length})`}>
            {linked.length === 0 ? (
              <EmptyState>No other case shares an identifier with this one.</EmptyState>
            ) : (
              <ul className="space-y-2">
                {linked.map((item) => (
                  <li key={item.case.case_id} className="rounded-lg border border-slate-200 p-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <Link
                        to={`/investigate/case/${item.case.case_id}`}
                        className="font-mono text-xs font-bold text-blue-700 hover:underline"
                      >
                        {item.case.case_id}
                      </Link>
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-600">
                        link {item.link_strength}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-1.5">
                      <ArtifactTag type={item.case.artifact_type} />
                      <RiskBadge level={item.case.risk_level} />
                    </div>
                    <p className="mt-1 break-words font-mono text-[11px] text-slate-500">
                      {item.shared_identifiers.join(', ')}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title={`Repeat content (${similar.length})`}>
            {similar.length === 0 ? (
              <EmptyState>No matching or near-duplicate content found.</EmptyState>
            ) : (
              <ul className="space-y-2">
                {similar.map((item) => (
                  <li
                    key={item.case.case_id}
                    className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 p-2.5"
                  >
                    <Link
                      to={`/investigate/case/${item.case.case_id}`}
                      className="font-mono text-xs font-bold text-blue-700 hover:underline"
                    >
                      {item.case.case_id}
                    </Link>
                    <span className="text-[10px] font-bold text-slate-600">
                      {item.match_type === 'EXACT_TEMPLATE' ? 'Same template' : `${item.similarity}% similar`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          {detail.details?.limitations?.length > 0 && (
            <Panel title="Limitations" muted>
              <ul className="list-disc space-y-1 pl-4 text-xs">
                {detail.details.limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </Panel>
          )}
        </div>
      </div>
    </div>
  )
}
