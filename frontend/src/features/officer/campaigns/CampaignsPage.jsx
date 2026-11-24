import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card, CardHeader, EmptyBlock, ErrorBlock, Icon, IdentifierChip, LoadingBlock, RiskBadge, Timeline } from '../../../design/ui'
import { officerApi } from '../../../lib/api'
import { ARTIFACT_META, PageHeader, formatDateTime } from '../shared'
import { NetworkGraph } from './NetworkGraph'

// Built from design/stitch/parakh_campaign_intelligence_syndicate_network_graph.
// GET /investigate/campaigns groups cases that share identifiers or near-
// duplicate text (app/services/campaign_service.py). The timeline shows how
// the scam text changed between variants and which new identifiers appeared.

const MAX_GRAPH_NODES = 160

function CampaignTimeline({ campaign }) {
  const items = campaign.timeline.map((entry) => ({
    id: entry.case_id,
    time: formatDateTime(entry.created_at),
    tone: entry.risk_level === 'HIGH' ? 'high' : entry.risk_level === 'LOW' ? 'low' : 'medium',
    title: (
      <Link to={`/investigate/case/${encodeURIComponent(entry.case_id)}`} className="font-mono text-primary hover:underline">
        {entry.case_id}
      </Link>
    ),
    body: (
      <div className="space-y-1">
        <p>{entry.preview || entry.summary}</p>
        {entry.variant_of && (
          <p className="text-ink-3">
            Variant of <span className="font-mono">{entry.variant_of}</span>
            {typeof entry.similarity === 'number' && ` · ${entry.similarity}% similar`}
          </p>
        )}
        {entry.changes.length > 0 && (
          <ul className="space-y-0.5">
            {entry.changes.map((change, index) => (
              <li key={index} className="font-mono text-[12px]">
                {change.before && <span className="rounded bg-risk-high-bg px-1 text-risk-high-ink line-through">{change.before}</span>}
                {change.before && change.after && ' → '}
                {change.after && <span className="rounded bg-risk-low-bg px-1 text-risk-low-ink">{change.after}</span>}
              </li>
            ))}
          </ul>
        )}
        {entry.new_identifiers.length > 0 && (
          <p className="text-ink-3">New identifiers: <span className="font-mono text-ink-2">{entry.new_identifiers.join(', ')}</span></p>
        )}
      </div>
    ),
  }))
  return <Timeline label={`Timeline of ${campaign.name}`} items={items} />
}

export function CampaignsPage() {
  const navigate = useNavigate()
  const graph = useQuery({ queryKey: ['campaigns'], queryFn: () => officerApi.campaigns({}) })
  const [selected, setSelected] = useState(null)
  const data = graph.data
  const campaigns = data?.campaigns || []
  const active = campaigns.find((campaign) => campaign.campaign_id === selected) || null

  const view = useMemo(() => {
    if (!data) return { nodes: [], edges: [] }
    let nodes = active ? data.nodes.filter((node) => node.campaign_id === active.campaign_id) : data.nodes
    if (!active && nodes.length > MAX_GRAPH_NODES) {
      const keep = new Set(campaigns.slice(0, 6).map((campaign) => campaign.campaign_id))
      nodes = nodes.filter((node) => keep.has(node.campaign_id))
    }
    const ids = new Set(nodes.map((node) => node.id))
    return { nodes, edges: data.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)) }
  }, [data, active, campaigns])

  function onSelect(node) {
    if (node.kind === 'case') navigate(`/investigate/case/${encodeURIComponent(node.case_id)}`)
    else navigate(`/investigate/identifier/${node.identifier_type}/${encodeURIComponent(node.value)}`)
  }

  return (
    <div>
      <PageHeader title="Campaign map" hindi="ठगी अभियान मानचित्र" eyebrow="Linked cases">
        {data && (
          <p className="text-body-sm text-ink-2 tnum">
            {data.linked_case_count} of {data.cases_scanned} cases are linked into {campaigns.length} campaign{campaigns.length === 1 ? "" : "s"}
          </p>
        )}
      </PageHeader>

      {graph.isPending && <LoadingBlock rows={8} />}
      {graph.isError && <Card><ErrorBlock error={graph.error} onRetry={() => graph.refetch()} /></Card>}
      {data && campaigns.length === 0 && (
        <Card>
          <EmptyBlock icon="hub" title="No campaigns yet">
            A campaign appears when two or more cases share a UPI ID, phone number, domain, app signer or near-identical text.
          </EmptyBlock>
        </Card>
      )}

      {data && campaigns.length > 0 && (
        <div className="grid gap-6 xl:grid-cols-[340px_1fr] [&>*]:min-w-0">
          <Card className="p-3">
            <p className="px-2 pt-2 text-label-ui uppercase text-ink-3">Campaigns</p>
            <ul className="mt-2 max-h-[640px] space-y-1 overflow-auto">
              <li>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  aria-pressed={!active}
                  className={`w-full rounded-chip px-3 py-2 text-left text-body-sm font-semibold ${!active ? 'bg-primary text-white' : 'text-ink-2 hover:bg-canvas'}`}
                >
                  All campaigns
                </button>
              </li>
              {campaigns.map((campaign) => {
                const on = active?.campaign_id === campaign.campaign_id
                return (
                  <li key={campaign.campaign_id}>
                    <button
                      type="button"
                      onClick={() => setSelected(campaign.campaign_id)}
                      aria-pressed={on}
                      className={`w-full rounded-chip border px-3 py-2 text-left ${on ? 'border-primary bg-primary-tint' : 'border-transparent hover:bg-canvas'}`}
                    >
                      <span className="flex items-center justify-between gap-2">
                        <span className="truncate text-body-sm font-semibold text-ink">{campaign.name}</span>
                        <RiskBadge level={campaign.risk_level} className="shrink-0" />
                      </span>
                      <span className="mt-0.5 block text-body-sm text-ink-3 tnum">
                        {campaign.case_count} cases · {Object.entries(campaign.artifact_mix).map(([key, value]) => `${value} ${ARTIFACT_META[key]?.label || key}`).join(', ')}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </Card>

          <div className="min-w-0 space-y-6">
            <Card className="p-5">
              <CardHeader
                title={active ? active.name : 'All linked cases'}
                hindi="केस और साझा पहचानकर्ता"
                action={<span className="text-body-sm text-ink-3">Click a node to open it</span>}
              />
              {!active && data.nodes.length > MAX_GRAPH_NODES && (
                <p className="mt-2 text-body-sm text-ink-3">Showing the six largest campaigns. Pick a campaign to see it alone.</p>
              )}
              <div className="mt-3">
                <NetworkGraph nodes={view.nodes} edges={view.edges} onSelect={onSelect} label={`Network of ${view.nodes.length} cases and identifiers`} />
              </div>
            </Card>

            {active && (
              <div className="grid gap-6 2xl:grid-cols-[1fr_1fr]">
                <Card className="p-5">
                  <CardHeader title="Key identifiers" hindi="मुख्य पहचानकर्ता" />
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {active.key_identifiers.map((item) => (
                      <IdentifierChip key={`${item.type}:${item.value}`} type={item.type} value={item.value} count={item.case_count} to={`/investigate/identifier/${item.type}/${encodeURIComponent(item.value)}`} />
                    ))}
                  </div>
                  <p className="mt-4 flex items-center gap-2 text-body-sm text-ink-2">
                    <Icon name="schedule" size={18} /> First seen {formatDateTime(active.first_seen)} · last seen {formatDateTime(active.last_seen)}
                  </p>
                </Card>
                <Card className="p-5">
                  <CardHeader title="How it evolved" hindi="समय के साथ बदलाव" />
                  <div className="mt-4 max-h-[520px] overflow-auto pr-2">
                    <CampaignTimeline campaign={active} />
                  </div>
                </Card>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default CampaignsPage
