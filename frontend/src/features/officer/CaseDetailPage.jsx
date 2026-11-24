import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, CardHeader, EmptyBlock, ErrorBlock, Icon, IdentifierChip, LoadingBlock, RiskBadge, RiskGauge, StateBlock, useToast } from '../../design/ui'
import { officerApi } from '../../lib/api'
import { identifierMeta } from '../../design/vocab'
import { highlightSegments } from '../../lib/highlight'
import { ArtifactTag, CaseLink, SourceTag, StatusPill, formatDateTime, openHtmlResponse, saveResponse } from './shared'

// Built from design/stitch/parakh_case_detail_forensic_dossier_prk_20261118_k7p2qx.
// Data: GET /cases/{id}, /linked, /similar; PATCH for status and notes;
// /report (HTML, optional redaction) and /report.json for the case file.

const SEVERITY_ORDER = { HIGH: 0, MEDIUM: 1, LOW: 2 }

function ContentPanel({ detail }) {
  const text = detail.content_text || ''
  const evidence = detail.findings.map((finding) => finding.evidence).filter((value) => value && value.length >= 3 && value.length <= 80)
  const segments = highlightSegments(text.slice(0, 20_000), evidence)
  if (!text) return null
  return (
    <Card className="p-5">
      <CardHeader title={detail.artifact_type === 'APK' ? 'Extracted facts' : 'Submitted content'} hindi="प्रस्तुत सामग्री" />
      <pre className="mt-3 max-h-[420px] overflow-auto whitespace-pre-wrap break-words rounded-chip bg-canvas p-4 font-mono text-body-sm leading-relaxed text-ink">
        {segments.map((segment, index) =>
          segment.flag === null ? <span key={index}>{segment.text}</span> : <mark key={index} className="rounded bg-risk-high-bg px-0.5 text-risk-high-ink">{segment.text}</mark>,
        )}
      </pre>
      {text.length > 20_000 && <p className="mt-2 text-body-sm text-ink-3">Showing the first 20,000 characters.</p>}
    </Card>
  )
}

function Findings({ findings }) {
  const sorted = [...findings].sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3))
  return (
    <Card className="p-5">
      <CardHeader title={`Findings (${findings.length})`} hindi="निष्कर्ष" />
      {sorted.length === 0 ? (
        <p className="mt-3 text-body-sm text-ink-2">No risk indicators were found.</p>
      ) : (
        <ul className="mt-3 divide-y divide-line-soft">
          {sorted.map((finding, index) => (
            <li key={`${finding.code}-${index}`} className="flex gap-3 py-3">
              <RiskBadge level={finding.severity} className="mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="font-mono text-label-ui text-ink-3">{finding.code}</p>
                <p className="text-body-md text-ink">{finding.explanation}</p>
                {finding.evidence && <p className="mt-0.5 break-all font-mono text-body-sm text-ink-2">{finding.evidence}</p>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function Identifiers({ identifiers }) {
  const groups = identifiers.reduce((acc, item) => {
    ;(acc[item.type] ||= []).push(item)
    return acc
  }, {})
  return (
    <Card className="p-5">
      <CardHeader title={`Identifiers (${identifiers.length})`} hindi="पहचानकर्ता" />
      {identifiers.length === 0 ? (
        <p className="mt-3 text-body-sm text-ink-2">No identifiers were extracted.</p>
      ) : (
        <div className="mt-3 space-y-3">
          {Object.entries(groups).map(([type, items]) => (
            <div key={type}>
              <p className="text-label-ui uppercase text-ink-3">{identifierMeta(type).label} · {items.length}</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {items.slice(0, 30).map((item) => (
                  <IdentifierChip key={item.value} type={item.type} value={item.value} to={`/investigate/identifier/${item.type}/${encodeURIComponent(item.value)}`} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

function Workflow({ detail }) {
  const client = useQueryClient()
  const toast = useToast()
  const [status, setStatus] = useState(detail.status)
  const [note, setNote] = useState(detail.officer_note || '')
  useEffect(() => {
    setStatus(detail.status)
    setNote(detail.officer_note || '')
  }, [detail.status, detail.officer_note])
  const save = useMutation({
    mutationFn: () => officerApi.updateCase(detail.case_id, { status, officer_note: note }),
    onSuccess: (updated) => {
      client.setQueryData(['case', detail.case_id], updated)
      client.invalidateQueries({ queryKey: ['cases'] })
      client.invalidateQueries({ queryKey: ['dashboard'] })
      toast('Case updated.', 'success')
    },
    onError: (error) => toast(error.message, 'error'),
  })
  const dirty = status !== detail.status || note !== (detail.officer_note || '')
  return (
    <Card className="p-5">
      <CardHeader title="Review" hindi="समीक्षा" />
      <div className="mt-3 space-y-3">
        <label className="block text-body-sm font-semibold text-ink">
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value)} className="mt-1 h-10 w-full rounded-chip border border-line bg-white px-3 text-body-sm">
            <option value="NEW">New</option>
            <option value="UNDER_REVIEW">Under review</option>
            <option value="CLOSED">Closed</option>
          </select>
        </label>
        <label className="block text-body-sm font-semibold text-ink">
          Officer note
          <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={4} maxLength={4000} className="mt-1 w-full rounded-chip border border-line bg-white p-3 text-body-sm font-normal" placeholder="Actions taken, FIR number, bank freeze request…" />
        </label>
        <Button icon="save" block loading={save.isPending} disabled={!dirty} onClick={() => save.mutate()}>Save</Button>
      </div>
      {detail.reporter_note && (
        <div className="mt-4 rounded-chip bg-canvas p-3 text-body-sm">
          <p className="text-label-ui uppercase text-ink-3">Reporter note</p>
          <p className="text-ink">{detail.reporter_note}</p>
        </div>
      )}
    </Card>
  )
}

function ReportActions({ caseId }) {
  const toast = useToast()
  const [busy, setBusy] = useState('')
  async function run(kind, task) {
    setBusy(kind)
    try {
      await task()
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setBusy('')
    }
  }
  return (
    <Card className="p-5">
      <CardHeader title="Case report" hindi="केस रिपोर्ट" />
      <div className="mt-3 grid gap-2">
        <Button variant="ghost" icon="description" className="justify-start" loading={busy === 'html'} onClick={() => run('html', async () => openHtmlResponse(await officerApi.reportHtml(caseId)))}>
          Open full report
        </Button>
        <Button variant="ghost" icon="visibility_off" className="justify-start" loading={busy === 'redacted'} onClick={() => run('redacted', async () => openHtmlResponse(await officerApi.reportHtml(caseId, true)))}>
          Open redacted report
        </Button>
        <Button variant="ghost" icon="data_object" className="justify-start" loading={busy === 'json'} onClick={() => run('json', async () => saveResponse(await officerApi.reportJson(caseId), `${caseId}.json`))}>
          Download JSON
        </Button>
      </div>
      <p className="mt-3 text-body-sm text-ink-3">The redacted report masks identifiers for sharing outside the investigation team.</p>
    </Card>
  )
}

function Related({ caseId }) {
  const linked = useQuery({ queryKey: ['case', caseId, 'linked'], queryFn: () => officerApi.linkedCases(caseId) })
  const similar = useQuery({ queryKey: ['case', caseId, 'similar'], queryFn: () => officerApi.similarCases(caseId) })
  return (
    <div className="grid gap-6 xl:grid-cols-2 [&>*]:min-w-0">
      <Card className="p-5">
        <CardHeader title="Linked by identifiers" hindi="साझा पहचानकर्ता से जुड़े केस" />
        <div className="mt-3">
          <StateBlock query={linked} isEmpty={(data) => !data.length} empty={<EmptyBlock icon="link_off" title="No other case shares an identifier" />}>
            {(data) => (
              <ul className="divide-y divide-line-soft">
                {data.map((item) => (
                  <li key={item.case.case_id} className="py-1">
                    <CaseLink summary={item.case} compact />
                    <div className="mb-2 ml-2 flex flex-wrap items-center gap-1.5 text-body-sm text-ink-3">
                      <span className="tnum">Strength {item.link_strength}</span>
                      {item.shared_identifiers.map((value) => (
                        <span key={value} className="rounded-chip bg-canvas px-2 py-0.5 font-mono text-ink-2">{value}</span>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </StateBlock>
        </div>
      </Card>
      <Card className="p-5">
        <CardHeader title="Same or near-same text" hindi="समान संदेश" />
        <div className="mt-3">
          <StateBlock query={similar} isEmpty={(data) => !data.length} empty={<EmptyBlock icon="content_copy" title="No near-duplicate text found" />}>
            {(data) => (
              <ul className="divide-y divide-line-soft">
                {data.map((item) => (
                  <li key={item.case.case_id} className="py-1">
                    <CaseLink summary={item.case} compact />
                    <p className="mb-2 ml-2 text-body-sm text-ink-3">
                      {item.match_type === 'EXACT_TEMPLATE' ? 'Same template' : 'Near duplicate'} · {item.similarity}% similar
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </StateBlock>
        </div>
      </Card>
    </div>
  )
}

export function CaseDetailPage() {
  const { caseId = '' } = useParams()
  const detail = useQuery({ queryKey: ['case', caseId], queryFn: () => officerApi.getCase(caseId), retry: false })

  if (detail.isPending) return <LoadingBlock rows={8} />
  if (detail.isError) {
    return (
      <Card>
        <ErrorBlock error={detail.error} title={detail.error.status === 404 ? `Case ${caseId} was not found` : undefined} onRetry={detail.error.status === 404 ? undefined : () => detail.refetch()} />
        <p className="pb-6 text-center"><Link to="/investigate/cases" className="font-semibold text-primary hover:underline">Back to cases</Link></p>
      </Card>
    )
  }
  const data = detail.data
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-hero border border-line bg-card p-5 shadow-l1 md:flex-row md:items-center">
        <div className="min-w-0 flex-1">
          <Link to="/investigate/cases" className="inline-flex items-center gap-1 text-body-sm font-semibold text-primary hover:underline">
            <Icon name="arrow_back" size={16} /> Cases
          </Link>
          <h1 className="mt-1 break-all font-mono text-headline-md text-ink">{data.case_id}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <RiskBadge level={data.risk_level} />
            <StatusPill status={data.status} />
            <ArtifactTag type={data.artifact_type} />
            <SourceTag source={data.source} />
            <span className="text-body-sm text-ink-3">{formatDateTime(data.created_at)}</span>
          </div>
          <p className="mt-3 max-w-3xl text-body-md text-ink">{data.summary}</p>
        </div>
        <RiskGauge value={data.risk_score} level={data.risk_level} caption="Risk score" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_360px] [&>*]:min-w-0">
        <div className="min-w-0 space-y-6">
          <Findings findings={data.findings} />
          <Identifiers identifiers={data.identifiers} />
          <ContentPanel detail={data} />
        </div>
        <div className="space-y-4">
          <Workflow detail={data} />
          <ReportActions caseId={data.case_id} />
        </div>
      </div>
      <Related caseId={data.case_id} />
    </div>
  )
}

export default CaseDetailPage
