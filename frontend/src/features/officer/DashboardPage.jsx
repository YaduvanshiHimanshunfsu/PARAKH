import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarList, ButtonLink, CHART_RISK, Card, CardHeader, Donut, EmptyBlock, ErrorBlock, Icon, KpiCard, LoadingBlock, Segmented } from '../../design/ui'
import { officerApi } from '../../lib/api'
import { useAuth } from '../../app/AuthContext'
import { StackedBars } from '../../design/ui/Charts'
import { ARTIFACT_META, CaseLink, PageHeader, formatDateTime } from './shared'

// Built from design/stitch/parakh_officer_dashboard_command_centre_1. Every
// number comes from GET /investigate/dashboard/summary (app/services/
// dashboard_service.py). The Stitch district choropleth needs current LGD
// district boundaries and a district field on cases (Phase C), so it is
// shown as a labelled placeholder instead of an invented map.

const PERIODS = [
  { value: '7', label: '7 days' },
  { value: '30', label: '30 days' },
  { value: '90', label: '90 days' },
]

const RISK_SERIES = [
  { key: 'low', label: 'Low', color: CHART_RISK.LOW },
  { key: 'medium', label: 'Medium', color: CHART_RISK.MEDIUM },
  { key: 'high', label: 'High', color: CHART_RISK.HIGH },
]

export function DashboardPage() {
  const { user } = useAuth()
  const [days, setDays] = useState('30')
  const summary = useQuery({
    queryKey: ['dashboard', days],
    queryFn: () => officerApi.dashboardSummary(Number(days)),
    refetchInterval: 60_000,
  })
  const data = summary.data

  return (
    <div>
      <PageHeader eyebrow={`Signed in as ${user?.username || 'officer'}`} title="Command dashboard" hindi="कमान डैशबोर्ड">
        <Segmented label="Period" size="sm" value={days} onChange={setDays} options={PERIODS} />
        <ButtonLink to="/investigate/submit" icon="add" size="sm">New analysis</ButtonLink>
      </PageHeader>

      {summary.isPending && <LoadingBlock rows={6} />}
      {summary.isError && (
        <Card>
          <ErrorBlock error={summary.error} onRetry={() => summary.refetch()} />
        </Card>
      )}

      {data && data.total_cases === 0 && (
        <Card>
          <EmptyBlock icon="inbox" title="No cases yet" action={<ButtonLink to="/investigate/submit" icon="add">Analyse the first item</ButtonLink>}>
            Submit a message, link, email, website or APK, or wait for citizens to send reports. The dashboard fills in from real cases.
          </EmptyBlock>
        </Card>
      )}

      {data && data.total_cases > 0 && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            <KpiCard label={`Cases · ${data.days} days`} value={data.cases_in_period} delta={`${data.total_cases} in total`} icon={<Icon name="folder_open" className="text-primary" />} />
            <KpiCard label="High risk" value={data.high_risk_in_period} tone="high" delta={data.cases_in_period ? `${Math.round((data.high_risk_in_period / data.cases_in_period) * 100)}% of period` : '—'} icon={<Icon name="gpp_maybe" className="text-risk-high-ink" />} />
            <KpiCard label="Awaiting review" value={data.unreviewed} tone="medium" delta={`${data.citizen_reports_new} citizen report${data.citizen_reports_new === 1 ? "" : "s"} new · ${data.new_today} today`} icon={<Icon name="pending_actions" className="text-risk-medium-ink" />} />
            <KpiCard label="Linked campaigns" value={data.campaigns} tone="primary" delta="Cases sharing identifiers or text" icon={<Icon name="hub" className="text-primary" />} />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr] [&>*]:min-w-0">
            <Card className="p-5">
              <CardHeader title="Cases by day and risk" hindi="दैनिक केस और जोखिम" />
              <div className="mt-4">
                <StackedBars series={RISK_SERIES} data={data.series} label={`Cases per day by risk level, last ${data.days} days`} />
              </div>
            </Card>
            <Card className="p-5">
              <CardHeader title="Risk mix" hindi="जोखिम वितरण" />
              <div className="mt-4">
                <Donut
                  label="Cases by risk level in this period"
                  centerLabel="cases"
                  segments={[
                    { label: 'High', value: data.risk_mix.HIGH || 0, color: CHART_RISK.HIGH },
                    { label: 'Medium', value: data.risk_mix.MEDIUM || 0, color: CHART_RISK.MEDIUM },
                    { label: 'Low', value: data.risk_mix.LOW || 0, color: CHART_RISK.LOW },
                  ]}
                />
              </div>
              <h3 className="mt-6 text-label-ui uppercase text-ink-3">By artifact</h3>
              <div className="mt-2">
                <BarList
                  label="Cases by artifact type in this period"
                  rows={Object.keys(ARTIFACT_META).map((key) => ({ label: ARTIFACT_META[key].label, value: data.artifact_mix[key] || 0 }))}
                />
              </div>
            </Card>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr] [&>*]:min-w-0">
            <Card className="p-5">
              <CardHeader
                title="Latest cases"
                hindi="नवीनतम केस"
                action={<Link to="/investigate/cases" className="text-body-sm font-semibold text-primary hover:underline">All cases →</Link>}
              />
              <ul className="mt-3 divide-y divide-line-soft">
                {data.recent_cases.map((item) => (
                  <li key={item.case_id}><CaseLink summary={item} /></li>
                ))}
              </ul>
            </Card>
            <div className="space-y-4">
              <Card className="p-5">
                <CardHeader title="Quick actions" />
                <div className="mt-3 grid gap-2">
                  <ButtonLink to="/investigate/cases?status=NEW" variant="ghost" icon="inbox" className="justify-start">Review new cases ({data.unreviewed})</ButtonLink>
                  <ButtonLink to="/investigate/heatlist" variant="ghost" icon="local_fire_department" className="justify-start">Rising identifiers</ButtonLink>
                  <ButtonLink to="/investigate/campaigns" variant="ghost" icon="hub" className="justify-start">Campaign map</ButtonLink>
                </div>
              </Card>
              <div className="rounded-card border border-dashed border-line p-5">
                <p className="flex items-center gap-2 text-title-md text-ink"><Icon name="map" className="text-ink-3" /> District map</p>
                <p className="mt-1 text-body-sm text-ink-2">
                  Needs a district field on each case and current district boundaries. Planned for Phase C; not shown until the data is real.
                </p>
              </div>
            </div>
          </div>
          <p className="text-body-sm text-ink-3">Computed from the case store at {formatDateTime(data.generated_at)}. Refreshes every minute.</p>
        </div>
      )}
    </div>
  )
}

export default DashboardPage
