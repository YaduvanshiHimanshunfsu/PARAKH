import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, CardHeader, EmptyBlock, Icon, StateBlock, useToast } from '../../../design/ui'
import { officerApi } from '../../../lib/api'
import { useAuth } from '../../../app/AuthContext'
import { DocumentCard } from './DocumentCard'

// The action pack on a case: what this case lets the officer demand, and from
// whom. Drafting is one click; sending is never automatic.

const CAN_DRAFT = ['IO', 'STATION_HEAD', 'SUPERVISOR', 'ADMIN', 'OFFICER']

export function ActionPackPanel({ caseId }) {
  const { user } = useAuth()
  const client = useQueryClient()
  const toast = useToast()
  const documents = useQuery({
    queryKey: ['case-documents', caseId],
    queryFn: () => officerApi.caseDocuments(caseId),
  })

  const generate = useMutation({
    mutationFn: () => officerApi.generateActionPack(caseId),
    onSuccess: (result) => {
      toast(
        result.created > 0
          ? `${result.created} draft${result.created === 1 ? '' : 's'} prepared.`
          : 'Every requisition for this case already exists.',
        'success',
      )
      client.invalidateQueries({ queryKey: ['case-documents', caseId] })
      client.invalidateQueries({ queryKey: ['queue'] })
    },
    onError: (error) => toast(error.message, 'error'),
  })

  const mayDraft = CAN_DRAFT.includes(user?.role)

  return (
    <Card className="p-5">
      <CardHeader
        title="Action pack"
        hindi="कानूनी पत्र"
        eyebrow="Requisitions"
        action={
          mayDraft ? (
            <Button size="sm" icon="auto_awesome" loading={generate.isPending} onClick={() => generate.mutate()}>
              {documents.data?.length ? 'Check for new drafts' : 'Draft requisitions'}
            </Button>
          ) : null
        }
      />
      <p className="mt-2 text-body-sm text-ink-2">
        PARAKH drafts the notices this case justifies — bank records and a freeze for a UPI ID,
        telecom records for a number, a takedown for a domain, and the evidence certificate. Each one
        is an unsigned draft until the chain of command approves it. Nothing is sent by PARAKH.
      </p>

      <div className="mt-4">
        <StateBlock
          query={documents}
          isEmpty={(value) => !value.length}
          empty={
            <EmptyBlock icon="description" title="No requisitions yet">
              {mayDraft
                ? 'Use “Draft requisitions” to prepare them from the identifiers in this case.'
                : 'An investigating officer can draft the requisitions for this case.'}
            </EmptyBlock>
          }
        >
          {(value) => (
            <div className="space-y-3">
              {value.map((document) => (
                <DocumentCard key={document.id} document={document} caseId={caseId} />
              ))}
            </div>
          )}
        </StateBlock>
      </div>

      <p className="mt-4 flex items-start gap-2 text-body-sm text-ink-3">
        <Icon name="gavel" size={16} className="mt-0.5 shrink-0" />
        Addressees are resolved from the identifier. Where a mapping can change — a UPI handle's
        sponsor bank, or a number that may have been ported — the draft says so and asks the officer
        to confirm before dispatch.
      </p>
    </Card>
  )
}
