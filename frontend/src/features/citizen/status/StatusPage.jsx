import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button, Card, ErrorBlock, Icon, LoadingBlock, Stepper } from '../../../design/ui'
import { citizenApi } from '../../../lib/api'

// Report status (planversionalpha.md H.5; no Stitch screen). Reads
// GET /parakh/report/{reference}/status, which returns only the stage of a
// citizen-filed report — never its content or any officer note.

const STAGES = ['NEW', 'UNDER_REVIEW', 'CLOSED']
const STAGE_TEXT = {
  NEW: ['Received', 'प्राप्त', 'Your report is in the police review queue.'],
  UNDER_REVIEW: ['Under review', 'समीक्षा में', 'An officer is reviewing your report and linking it with other cases.'],
  CLOSED: ['Review complete', 'समीक्षा पूरी', 'Officers have finished reviewing this report.'],
}

const REFERENCE = /^PRK-\d{8}-[A-Z0-9]{6}$/

function Lookup({ initial = '' }) {
  const [value, setValue] = useState(initial)
  const navigate = useNavigate()
  const clean = value.trim().toUpperCase()
  return (
    <form
      className="flex flex-wrap gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        if (REFERENCE.test(clean)) navigate(`/status/${clean}`)
      }}
    >
      <label htmlFor="reference" className="sr-only">Report reference</label>
      <input
        id="reference"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="PRK-20261124-ABC234"
        className="h-11 min-w-0 flex-1 rounded-chip border-[1.5px] border-line bg-white px-3 font-mono text-body-md uppercase outline-none focus:border-primary"
      />
      <Button type="submit" icon="search" disabled={!REFERENCE.test(clean)}>Track</Button>
    </form>
  )
}

export function StatusPage() {
  const { reference = '' } = useParams()
  const clean = reference.trim().toUpperCase()
  const valid = REFERENCE.test(clean)
  const status = useQuery({
    queryKey: ['report-status', clean],
    queryFn: () => citizenApi.reportStatus(clean),
    enabled: valid,
    retry: false,
  })
  const current = status.data ? STAGES.indexOf(status.data.status) : -1

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 md:px-8">
      <h1 className="text-headline-lg-mobile md:text-headline-lg">
        Track your report <span className="hi block text-accent-strong md:inline" lang="hi">/ रिपोर्ट की स्थिति</span>
      </h1>
      <div className="mt-4">
        <Lookup key={clean} initial={clean} />
      </div>

      <div className="mt-6">
        {!valid && (
          <p className="rounded-card border border-dashed border-line p-5 text-body-md text-ink-2">
            Enter the reference you received after sending a report, for example <span className="font-mono">PRK-20261124-ABC234</span>.
          </p>
        )}
        {valid && status.isPending && <LoadingBlock rows={3} />}
        {valid && status.isError && (
          <Card>
            <ErrorBlock
              error={status.error}
              title={status.error.status === 404 ? 'No report found with this reference' : undefined}
              onRetry={status.error.status === 404 ? undefined : () => status.refetch()}
            />
          </Card>
        )}
        {status.data && (
          <Card className="p-5 md:p-6">
            <p className="text-label-ui uppercase text-ink-3">Reference</p>
            <p className="font-mono text-title-md text-ink">{status.data.reference}</p>
            <div className="mt-6">
              <Stepper
                label="Report progress"
                steps={STAGES.map((stage, index) => ({
                  label: STAGE_TEXT[stage][0],
                  hindi: STAGE_TEXT[stage][1],
                  status: index < current || (index === current && stage === 'CLOSED') ? 'done' : index === current ? 'current' : 'todo',
                }))}
              />
            </div>
            <p className="mt-5 text-body-md text-ink">{STAGE_TEXT[status.data.status]?.[2]}</p>
            <dl className="mt-4 grid gap-3 text-body-sm sm:grid-cols-2">
              <div>
                <dt className="text-ink-3">Received</dt>
                <dd className="text-ink tnum">{new Date(status.data.received_at).toLocaleString('en-IN')}</dd>
              </div>
              <div>
                <dt className="text-ink-3">Last updated</dt>
                <dd className="text-ink tnum">{new Date(status.data.updated_at).toLocaleString('en-IN')}</dd>
              </div>
            </dl>
          </Card>
        )}
      </div>

      <div className="mt-6 flex gap-3 rounded-card bg-sand p-4 text-body-sm text-ink-2">
        <Icon name="info" className="shrink-0 text-accent-strong" />
        <p>
          A PARAKH report helps police spot fraud patterns. It is not an FIR or a complaint on the National Cyber Crime Reporting Portal. If you lost money, call{' '}
          <a href="tel:1930" className="font-semibold text-primary">1930</a> and file at{' '}
          <a href="https://cybercrime.gov.in/" target="_blank" rel="noreferrer" className="font-semibold text-primary underline">cybercrime.gov.in</a>.
        </p>
      </div>
    </div>
  )
}

export default StatusPage
