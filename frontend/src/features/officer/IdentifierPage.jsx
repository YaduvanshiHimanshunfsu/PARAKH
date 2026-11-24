import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ButtonLink, CHART_RISK, Card, CardHeader, Donut, EmptyBlock, ErrorBlock, IdentifierChip, LoadingBlock, Timeline } from '../../design/ui'
import { IDENTIFIER_META, identifierMeta } from '../../design/vocab'
import { officerApi } from '../../lib/api'
import { ARTIFACT_META, PageHeader, formatDateTime } from './shared'

// Identifier pivot (planversionalpha.md H.5; no Stitch screen). Every case
// that mentions one UPI ID / number / domain / signer, oldest first, so an
// officer can see how long it has been active and in which kinds of fraud.

export function IdentifierPage() {
  const { type = '', value = '' } = useParams()
  const known = Boolean(IDENTIFIER_META[type])
  const cases = useQuery({
    queryKey: ['identifier', type, value],
    queryFn: () => officerApi.identifierCases(type, value),
    enabled: known && Boolean(value),
    retry: false,
  })
  const meta = identifierMeta(type)

  if (!known) {
    return (
      <Card>
        <EmptyBlock icon="help" title={`“${type}” is not an identifier type`} action={<ButtonLink to="/investigate/heatlist">Heat-list</ButtonLink>} />
      </Card>
    )
  }

  const list = cases.data?.cases || []
  const ordered = [...list].sort((a, b) => a.created_at.localeCompare(b.created_at))
  const risk = list.reduce((acc, item) => ({ ...acc, [item.risk_level]: (acc[item.risk_level] || 0) + 1 }), {})
  const artifacts = list.reduce((acc, item) => ({ ...acc, [item.artifact_type]: (acc[item.artifact_type] || 0) + 1 }), {})

  return (
    <div>
      <PageHeader eyebrow={`${meta.label} profile`} title="Identifier pivot" hindi="पहचानकर्ता प्रोफ़ाइल">
        <ButtonLink to={`/investigate/cases?q=${encodeURIComponent(value)}`} variant="ghost" size="sm" icon="search">Full-text search</ButtonLink>
      </PageHeader>
      <Card className="mb-6 p-5">
        <IdentifierChip type={type} value={value} />
      </Card>

      {cases.isPending && <LoadingBlock rows={6} />}
      {cases.isError && <Card><ErrorBlock error={cases.error} onRetry={() => cases.refetch()} /></Card>}
      {cases.data && list.length === 0 && (
        <Card>
          <EmptyBlock icon="search_off" title="No case mentions this identifier">
            It may be written differently in case text. Try the full-text search.
          </EmptyBlock>
        </Card>
      )}
      {list.length > 0 && (
        <div className="grid gap-6 xl:grid-cols-[1fr_360px] [&>*]:min-w-0">
          <Card className="p-5">
            <CardHeader title={`${list.length} case${list.length === 1 ? '' : 's'}, oldest first`} hindi="केस समयरेखा" />
            <div className="mt-4">
              <Timeline
                label={`Cases mentioning ${value}`}
                items={ordered.map((item) => ({
                  id: item.case_id,
                  time: formatDateTime(item.created_at),
                  tone: item.risk_level === 'HIGH' ? 'high' : item.risk_level === 'LOW' ? 'low' : 'medium',
                  title: (
                    <Link to={`/investigate/case/${encodeURIComponent(item.case_id)}`} className="font-mono text-primary hover:underline">
                      {item.case_id}
                    </Link>
                  ),
                  body: `${ARTIFACT_META[item.artifact_type]?.label || item.artifact_type} · ${item.preview || item.summary}`,
                }))}
              />
            </div>
          </Card>
          <div className="space-y-4">
            <Card className="p-5">
              <CardHeader title="Activity" />
              <dl className="mt-3 space-y-2 text-body-sm">
                <div className="flex justify-between gap-2"><dt className="text-ink-3">First seen</dt><dd className="text-ink tnum">{formatDateTime(ordered[0].created_at)}</dd></div>
                <div className="flex justify-between gap-2"><dt className="text-ink-3">Last seen</dt><dd className="text-ink tnum">{formatDateTime(ordered[ordered.length - 1].created_at)}</dd></div>
                <div className="flex justify-between gap-2"><dt className="text-ink-3">Citizen reports</dt><dd className="text-ink tnum">{list.filter((item) => item.source === 'CITIZEN').length}</dd></div>
                <div className="flex justify-between gap-2"><dt className="text-ink-3">Types</dt><dd className="text-right text-ink">{Object.entries(artifacts).map(([key, count]) => `${count} ${ARTIFACT_META[key]?.label || key}`).join(', ')}</dd></div>
              </dl>
            </Card>
            <Card className="p-5">
              <CardHeader title="Risk of these cases" />
              <div className="mt-3">
                <Donut
                  label="Cases by risk level"
                  centerLabel="cases"
                  segments={[
                    { label: 'High', value: risk.HIGH || 0, color: CHART_RISK.HIGH },
                    { label: 'Medium', value: risk.MEDIUM || 0, color: CHART_RISK.MEDIUM },
                    { label: 'Low', value: risk.LOW || 0, color: CHART_RISK.LOW },
                  ]}
                />
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}

export default IdentifierPage
