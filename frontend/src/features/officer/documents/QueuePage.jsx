import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card, EmptyBlock, Icon, StateBlock } from '../../../design/ui'
import { officerApi } from '../../../lib/api'
import { useAuth } from '../../../app/AuthContext'
import { PageHeader } from '../shared'
import { DocumentCard } from './DocumentCard'

// What is waiting for *this* officer, most overdue first. The queue is how a
// chain of command stops being a diagram and starts being work.

const ROLE_EXPLAINER = {
  IO: 'You draft requisitions. Once submitted they wait with your station head.',
  OPERATOR: 'Your role submits items for analysis; approvals sit with the station head.',
  STATION_HEAD: 'Requisitions from your station wait here for station-level approval.',
  SUPERVISOR: 'Freezes and takedowns from the district reach you for final approval.',
  STATE_VIEWER: 'Your role is read-only, so nothing waits for your approval.',
  ADMIN: 'Administrator: every pending requisition is visible.',
  OFFICER: 'Shared officer account: every pending requisition is visible.',
}

export function QueuePage() {
  const { user } = useAuth()
  const queue = useQuery({ queryKey: ['queue'], queryFn: officerApi.queue, refetchInterval: 60_000 })
  const data = queue.data

  return (
    <div>
      <PageHeader title="My queue" hindi="मेरी सूची" eyebrow="Awaiting my action">
        {data && (
          <p className="text-body-sm text-ink-2 tnum">
            {data.total} waiting
            {data.overdue > 0 && <span className="ml-2 font-semibold text-risk-high-ink">{data.overdue} overdue</span>}
          </p>
        )}
      </PageHeader>

      <p className="mb-4 flex items-start gap-2 rounded-card border border-line bg-card p-4 text-body-sm text-ink-2">
        <Icon name="info" className="shrink-0 text-primary" size={18} />
        {ROLE_EXPLAINER[user?.role] || 'Requisitions waiting for your approval appear here.'}
      </p>

      <StateBlock
        query={queue}
        isEmpty={(value) => !value.documents.length}
        empty={
          <Card>
            <EmptyBlock icon="inbox" title="Nothing is waiting for you">
              When an officer submits a requisition for approval at your level, it appears here with
              its deadline.
            </EmptyBlock>
          </Card>
        }
      >
        {(value) => (
          <div className="space-y-4">
            {value.documents.map((document) => (
              <div key={document.id}>
                <Link
                  to={`/investigate/case/${encodeURIComponent(document.case_id)}`}
                  className="mb-1 inline-block font-mono text-body-sm text-primary hover:underline"
                >
                  {document.case_id}
                </Link>
                <DocumentCard document={document} caseId={document.case_id} />
              </div>
            ))}
          </div>
        )}
      </StateBlock>
    </div>
  )
}

export default QueuePage
