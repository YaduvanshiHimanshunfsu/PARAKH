import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Button, ButtonLink, Card, EmptyBlock, ErrorBlock, Icon, LoadingBlock, RiskBadge, useToast } from '../../design/ui'
import { officerApi } from '../../lib/api'
import { guessIdentifierType } from '../../lib/identifiers'
import { identifierMeta } from '../../design/vocab'
import { ARTIFACT_META, ArtifactTag, PageHeader, SourceTag, StatusPill, formatDateTime, saveResponse, timeAgo } from './shared'

// Built from design/stitch/parakh_case_table_empty_loading_error_states.
// Filters live in the URL so a filtered view can be shared or bookmarked.

const PAGE = 25
const selectClass = 'h-10 rounded-chip border border-line bg-white px-3 text-body-sm'

function useFilters() {
  const [params, setParams] = useSearchParams()
  const filters = {
    q: params.get('q') || '',
    artifact_type: params.get('artifact_type') || '',
    risk_level: params.get('risk_level') || '',
    status: params.get('status') || '',
    mine: params.get('mine') === 'true',
    page: Math.max(0, Number(params.get('page')) || 0),
  }
  function update(patch) {
    const next = { ...filters, page: 0, ...patch }
    const search = new URLSearchParams()
    Object.entries(next).forEach(([key, value]) => {
      if (value && !(key === 'page' && value === 0)) search.set(key, String(value))
    })
    setParams(search, { replace: true })
  }
  return [filters, update]
}

export function CasesPage() {
  const [filters, update] = useFilters()
  const [draft, setDraft] = useState(filters.q)
  const [exporting, setExporting] = useState('')
  const toast = useToast()
  const apiFilters = {
    q: filters.q || undefined,
    artifact_type: filters.artifact_type || undefined,
    risk_level: filters.risk_level || undefined,
    status: filters.status || undefined,
  }
  const cases = useQuery({
    queryKey: ['cases', filters],
    queryFn: () => officerApi.searchCases({ ...apiFilters, mine: filters.mine || undefined, limit: PAGE, offset: filters.page * PAGE }),
    placeholderData: keepPreviousData,
  })
  const identifierType = guessIdentifierType(filters.q)
  const anyFilter = Boolean(filters.q || filters.artifact_type || filters.risk_level || filters.status || filters.mine)

  async function exportCsv(kind) {
    setExporting(kind)
    try {
      const response = kind === 'cases' ? await officerApi.exportCasesCsv(apiFilters) : await officerApi.exportIdentifiersCsv(apiFilters)
      await saveResponse(response, `parakh-${kind}.csv`)
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setExporting('')
    }
  }

  const data = cases.data
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE)) : 1

  return (
    <div>
      <PageHeader title="Cases" hindi="केस रजिस्टर">
        <Button variant="ghost" size="sm" icon="download" loading={exporting === 'cases'} onClick={() => exportCsv('cases')}>Cases CSV</Button>
        <Button variant="ghost" size="sm" icon="download" loading={exporting === 'identifiers'} onClick={() => exportCsv('identifiers')}>Identifiers CSV</Button>
      </PageHeader>

      <Card className="p-4">
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            update({ q: draft.trim() })
          }}
        >
          <label className="relative min-w-[220px] flex-1">
            <span className="sr-only">Search cases</span>
            <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" size={20} />
            <input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Case ID, text, UPI, phone, domain…" className="h-10 w-full rounded-chip border border-line bg-white pl-10 pr-3 text-body-sm outline-none focus:border-primary" />
          </label>
          <select aria-label="Artifact type" value={filters.artifact_type} onChange={(event) => update({ artifact_type: event.target.value })} className={selectClass}>
            <option value="">All types</option>
            {Object.entries(ARTIFACT_META).map(([key, meta]) => <option key={key} value={key}>{meta.label}</option>)}
          </select>
          <select aria-label="Risk level" value={filters.risk_level} onChange={(event) => update({ risk_level: event.target.value })} className={selectClass}>
            <option value="">All risk</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
          <select aria-label="Status" value={filters.status} onChange={(event) => update({ status: event.target.value })} className={selectClass}>
            <option value="">All status</option>
            <option value="NEW">New</option>
            <option value="UNDER_REVIEW">Under review</option>
            <option value="CLOSED">Closed</option>
          </select>
          <label className="flex h-10 items-center gap-2 rounded-chip border border-line bg-white px-3 text-body-sm">
            <input type="checkbox" checked={filters.mine} onChange={(event) => update({ mine: event.target.checked })} className="accent-[#1d4ed8]" />
            Mine
          </label>
          <Button type="submit" size="sm" icon="search">Search</Button>
          {anyFilter && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setDraft('')
                update({ q: '', artifact_type: '', risk_level: '', status: '', mine: false })
              }}
            >
              Clear
            </Button>
          )}
        </form>
        {identifierType && filters.q && (
          <p className="mt-3 flex flex-wrap items-center gap-2 text-body-sm text-ink-2">
            <Icon name="lightbulb" size={18} className="text-accent-strong" />
            This looks like a {identifierMeta(identifierType).label}.
            <Link to={`/investigate/identifier/${identifierType}/${encodeURIComponent(filters.q)}`} className="font-semibold text-primary hover:underline">
              Open its identifier profile →
            </Link>
          </p>
        )}
      </Card>

      <Card className="mt-4 overflow-hidden">
        {cases.isPending && <div className="p-4"><LoadingBlock rows={6} /></div>}
        {cases.isError && <ErrorBlock error={cases.error} onRetry={() => cases.refetch()} />}
        {data && data.cases.length === 0 && (
          <EmptyBlock
            icon={anyFilter ? 'search_off' : 'inbox'}
            title={anyFilter ? 'No cases match these filters' : 'No cases yet'}
            action={anyFilter ? null : <ButtonLink to="/investigate/submit" icon="add">New analysis</ButtonLink>}
          >
            {anyFilter ? 'Try a broader search or clear a filter.' : 'Cases appear here when officers submit items or citizens send reports.'}
          </EmptyBlock>
        )}
        {data && data.cases.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className={`w-full min-w-[860px] text-body-sm ${cases.isFetching ? 'opacity-60' : ''}`}>
                <caption className="sr-only">Case search results</caption>
                <thead className="bg-canvas text-left text-label-ui uppercase text-ink-3">
                  <tr>
                    <th className="px-4 py-3">Case</th>
                    <th className="px-4 py-3">Risk</th>
                    <th className="px-4 py-3">Summary</th>
                    <th className="px-4 py-3">IDs</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Received</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line-soft">
                  {data.cases.map((item) => (
                    <tr key={item.case_id} className="hover:bg-canvas">
                      <td className="px-4 py-3 align-top">
                        <Link to={`/investigate/case/${encodeURIComponent(item.case_id)}`} className="font-mono font-semibold text-primary hover:underline">{item.case_id}</Link>
                        <div className="mt-0.5 flex gap-3"><ArtifactTag type={item.artifact_type} /><SourceTag source={item.source} /></div>
                      </td>
                      <td className="px-4 py-3 align-top"><RiskBadge level={item.risk_level} score={item.risk_score} /></td>
                      <td className="max-w-[360px] px-4 py-3 align-top">
                        <p className="line-clamp-2 text-ink">{item.summary}</p>
                        {item.preview && <p className="mt-0.5 truncate text-ink-3">{item.preview}</p>}
                      </td>
                      <td className="px-4 py-3 align-top tnum text-ink-2">{item.identifier_count}</td>
                      <td className="px-4 py-3 align-top"><StatusPill status={item.status} /></td>
                      <td className="px-4 py-3 align-top text-ink-2" title={formatDateTime(item.created_at)}>{timeAgo(item.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-3 text-body-sm text-ink-2">
              <span className="tnum">
                {filters.page * PAGE + 1}–{filters.page * PAGE + data.cases.length} of {data.total}
              </span>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" icon="chevron_left" disabled={filters.page === 0} onClick={() => update({ ...filters, page: filters.page - 1 })}>Previous</Button>
                <Button variant="ghost" size="sm" iconRight="chevron_right" disabled={filters.page + 1 >= pages} onClick={() => update({ ...filters, page: filters.page + 1 })}>Next</Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  )
}

export default CasesPage
