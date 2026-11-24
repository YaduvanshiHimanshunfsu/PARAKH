import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button, Card, Icon, Modal, useToast } from '../../../design/ui'
import { officerApi } from '../../../lib/api'
import { useAuth } from '../../../app/AuthContext'
import { openHtmlResponse } from '../shared'
import { CHANNELS, allowedActions, docMeta, statusMeta } from './documentVocab'

// One requisition, with the actions this officer may take on it. Every action
// is a real API call; the server re-checks the rule, so a hidden button is a
// convenience, never the control.

export function StatusPill({ status }) {
  const meta = statusMeta(status)
  return <span className={`inline-flex rounded-chip px-2 py-0.5 text-label-ui uppercase ${meta.tone}`}>{meta.label}</span>
}

function Field({ label, children }) {
  return (
    <div>
      <p className="text-label-ui uppercase text-ink-3">{label}</p>
      <div className="text-body-sm text-ink">{children}</div>
    </div>
  )
}

function ChainOfCommand({ approvals }) {
  if (!approvals?.length) return null
  return (
    <ol className="mt-3 space-y-2 border-l-2 border-line pl-4">
      {approvals.map((entry, index) => (
        <li key={index} className="relative">
          <span
            className={`absolute -left-[22px] top-1.5 h-3 w-3 rounded-full ring-4 ring-white ${
              entry.action === 'RETURN' ? 'bg-risk-medium' : entry.action === 'APPROVE' ? 'bg-risk-low' : 'bg-primary'
            }`}
          />
          <p className="text-body-sm font-semibold text-ink">
            {entry.action === 'SUBMIT' && 'Submitted for approval'}
            {entry.action === 'APPROVE' && `Approved at ${entry.stage.toLowerCase()} level`}
            {entry.action === 'RETURN' && 'Returned for correction'}
            {entry.action === 'DISPATCH' && 'Dispatched'}
            {entry.action === 'RESPONSE' && 'Reply recorded'}
            {entry.action === 'CLOSE' && 'Closed'}
            {entry.action === 'CANCEL' && 'Cancelled'}
          </p>
          <p className="text-body-sm text-ink-2">
            {entry.actor_rank ? `${entry.actor_rank} ` : ''}
            {entry.actor_name} · {new Date(entry.at).toLocaleString('en-IN')}
          </p>
          {entry.comment && <p className="mt-0.5 text-body-sm italic text-ink-2">“{entry.comment}”</p>}
        </li>
      ))}
    </ol>
  )
}

export function DocumentCard({ document, caseId, expanded = false }) {
  const { user } = useAuth()
  const client = useQueryClient()
  const toast = useToast()
  const [open, setOpen] = useState(expanded)
  const [dialog, setDialog] = useState(null)
  const [text, setText] = useState('')
  const [channel, setChannel] = useState('EMAIL')
  const meta = docMeta(document.doc_type)
  const can = allowedActions(document, user?.role)

  const refresh = () => {
    client.invalidateQueries({ queryKey: ['case-documents', caseId] })
    client.invalidateQueries({ queryKey: ['queue'] })
    client.invalidateQueries({ queryKey: ['document', document.id] })
  }

  const act = useMutation({
    mutationFn: ({ kind, value }) => {
      if (kind === 'submit') return officerApi.submitDocument(document.id)
      if (kind === 'approve') return officerApi.approveDocument(document.id, value)
      if (kind === 'return') return officerApi.returnDocument(document.id, value)
      if (kind === 'dispatch') return officerApi.dispatchDocument(document.id, { channel, reference: value })
      if (kind === 'respond') return officerApi.recordDocumentResponse(document.id, value)
      if (kind === 'close') return officerApi.closeDocument(document.id)
      if (kind === 'cancel') return officerApi.cancelDocument(document.id, value)
      throw new Error(`Unknown action: ${kind}`)
    },
    onSuccess: (updated) => {
      toast(`${meta.short}: ${statusMeta(updated.status).label.toLowerCase()}.`, 'success')
      setDialog(null)
      setText('')
      refresh()
    },
    onError: (error) => toast(error.message, 'error'),
  })

  const print = useMutation({
    mutationFn: async () => openHtmlResponse(await officerApi.documentPrint(document.id)),
    onError: (error) => toast(error.message, 'error'),
  })

  function run(kind, needsText) {
    if (needsText) {
      setDialog({ kind, needsText })
      return
    }
    act.mutate({ kind })
  }

  return (
    <Card className={`p-4 ${document.overdue ? 'border-risk-high/40' : ''}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="flex flex-wrap items-center gap-2 text-title-md text-ink">
            <Icon name={meta.icon} className="text-primary" size={20} />
            {document.title}
          </p>
          <p className="text-body-sm text-ink-2">
            <span className="font-mono">{document.doc_no}</span> · {document.legal_basis}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusPill status={document.status} />
          {document.overdue && (
            <span className="inline-flex items-center gap-1 text-body-sm font-semibold text-risk-high-ink">
              <Icon name="schedule" size={16} /> Overdue
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Field label="To">
          {document.addressee_display}
          {document.addressee_is_sample && (
            <span className="ml-1 rounded-chip bg-canvas px-1.5 py-0.5 text-[11px] text-ink-3">
              replace with the official nodal contact
            </span>
          )}
        </Field>
        <Field label="Subject identifiers">
          {document.subject_identifiers?.length ? (
            <span className="font-mono">{document.subject_identifiers.map((item) => item.value).join(', ')}</span>
          ) : (
            <span className="text-ink-3">Case evidence</span>
          )}
        </Field>
      </div>

      {document.due_at && ['PENDING_STATION', 'PENDING_SUPERVISOR'].includes(document.status) && (
        <p className="mt-2 text-body-sm text-ink-2">
          Due {new Date(document.due_at).toLocaleString('en-IN')}
        </p>
      )}
      {document.dispatch_ref && (
        <p className="mt-2 text-body-sm text-ink-2">
          Dispatched {document.dispatch_channel?.toLowerCase()} · ref <span className="font-mono">{document.dispatch_ref}</span>
        </p>
      )}
      {document.edited_after_approval && (
        <p className="mt-2 flex items-center gap-1 text-body-sm font-semibold text-risk-high-ink">
          <Icon name="warning" size={16} /> This copy differs from the one that was approved.
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="ghost" size="sm" icon="print" loading={print.isPending} onClick={() => print.mutate()}>
          Open
        </Button>
        {can.submit && <Button size="sm" icon="send" loading={act.isPending} onClick={() => run('submit')}>Submit for approval</Button>}
        {can.approve && <Button size="sm" icon="check" onClick={() => run('approve', true)}>Approve</Button>}
        {can.return && <Button variant="ghost" size="sm" icon="undo" onClick={() => run('return', true)}>Return</Button>}
        {can.dispatch && <Button size="sm" icon="outgoing_mail" onClick={() => run('dispatch', true)}>Record dispatch</Button>}
        {can.respond && <Button variant="ghost" size="sm" icon="mark_email_read" onClick={() => run('respond', true)}>Record reply</Button>}
        {can.close && <Button variant="ghost" size="sm" icon="task_alt" onClick={() => run('close')}>Close</Button>}
        {(document.approvals?.length > 0 || open) && (
          <Button variant="ghost" size="sm" icon={open ? 'expand_less' : 'expand_more'} onClick={() => setOpen(!open)}>
            {open ? 'Hide trail' : 'Approval trail'}
          </Button>
        )}
      </div>

      {open && <ChainOfCommand approvals={document.approvals} />}

      <Modal
        open={Boolean(dialog)}
        onClose={() => setDialog(null)}
        title={
          dialog?.kind === 'approve'
            ? 'Approve this requisition'
            : dialog?.kind === 'return'
              ? 'Return for correction'
              : dialog?.kind === 'dispatch'
                ? 'Record dispatch'
                : dialog?.kind === 'respond'
                  ? 'Record the reply'
                  : 'Cancel the requisition'
        }
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setDialog(null)}>Cancel</Button>
            <Button
              size="sm"
              loading={act.isPending}
              disabled={dialog?.kind !== 'approve' && !text.trim()}
              onClick={() => act.mutate({ kind: dialog.kind, value: text.trim() })}
            >
              Confirm
            </Button>
          </>
        }
      >
        {dialog?.kind === 'dispatch' && (
          <label className="mb-3 block text-body-sm font-semibold text-ink">
            Channel
            <select
              value={channel}
              onChange={(event) => setChannel(event.target.value)}
              className="mt-1 h-10 w-full rounded-chip border border-line bg-white px-3 text-body-sm"
            >
              {CHANNELS.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
        )}
        <label className="block text-body-sm font-semibold text-ink">
          {dialog?.kind === 'approve' && 'Comment (optional)'}
          {dialog?.kind === 'return' && 'What must be corrected?'}
          {dialog?.kind === 'dispatch' && 'Dispatch reference'}
          {dialog?.kind === 'respond' && 'What did they reply?'}
          {dialog?.kind === 'cancel' && 'Reason for cancelling'}
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={3}
            className="mt-1 w-full rounded-chip border border-line bg-white p-3 text-body-sm font-normal"
            placeholder={dialog?.kind === 'dispatch' ? 'e.g. JPR/CYBER/OUT/2026/114' : ''}
          />
        </label>
      </Modal>
    </Card>
  )
}
