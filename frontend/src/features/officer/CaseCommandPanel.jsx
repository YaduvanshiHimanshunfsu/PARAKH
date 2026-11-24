import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, CardHeader, Icon, Modal, Timeline, useToast } from '../../design/ui'
import { officerApi } from '../../lib/api'
import { useAuth } from '../../app/AuthContext'
import { formatDateTime } from './shared'

// Chain of command on one case: who owns it, who may act, and the audited
// record of everything already done to it.

const UNITS = [
  { code: 'JPR-CYBER-PS', name: 'Cyber Police Station, Jaipur' },
  { code: 'JPR-SOUTH-PS', name: 'Jaipur South Police Station' },
  { code: 'BTP-CYBER-PS', name: 'Cyber Police Station, Bharatpur' },
  { code: 'JPR-COMM', name: 'Jaipur Commissionerate' },
]

const OFFENCE_ACTS = [
  { value: 'IT_ACT', label: 'IT Act 2000' },
  { value: 'BNS', label: 'BNS 2023' },
  { value: 'BOTH', label: 'Both' },
  { value: 'UNKNOWN', label: 'Not decided' },
]

const MAY_ASSIGN = ['STATION_HEAD', 'SUPERVISOR', 'ADMIN', 'OFFICER']
const MAY_VERIFY = MAY_ASSIGN

export function CaseCommandPanel({ detail }) {
  const { user } = useAuth()
  const client = useQueryClient()
  const toast = useToast()
  const [dialog, setDialog] = useState(null)
  const [assignee, setAssignee] = useState('')
  const [offenceAct, setOffenceAct] = useState('IT_ACT')
  const [unitCode, setUnitCode] = useState(UNITS[0].code)
  const [reason, setReason] = useState('')

  const audit = useQuery({
    queryKey: ['case-audit', detail.case_id],
    queryFn: () => officerApi.caseAudit(detail.case_id),
  })

  const refresh = () => {
    client.invalidateQueries({ queryKey: ['case', detail.case_id] })
    client.invalidateQueries({ queryKey: ['case-audit', detail.case_id] })
    client.invalidateQueries({ queryKey: ['cases'] })
  }

  const act = useMutation({
    mutationFn: ({ kind }) => {
      if (kind === 'assign')
        return officerApi.assignCase(detail.case_id, {
          assignee_username: assignee.trim(),
          offence_act: offenceAct,
          reason: reason.trim() || null,
        })
      if (kind === 'transfer')
        return officerApi.transferCase(detail.case_id, { unit_code: unitCode, reason: reason.trim() })
      return officerApi.verifyCase(detail.case_id)
    },
    onSuccess: (_result, variables) => {
      toast(
        variables.kind === 'assign'
          ? 'Case assigned.'
          : variables.kind === 'transfer'
            ? 'Case transferred.'
            : 'Citizen report verified; it now counts as intelligence.',
        'success',
      )
      setDialog(null)
      setReason('')
      refresh()
    },
    onError: (error) => toast(error.message, 'error'),
  })

  const mayAssign = MAY_ASSIGN.includes(user?.role)
  const mayVerify = MAY_VERIFY.includes(user?.role) && detail.source === 'CITIZEN'
  const entries = audit.data?.entries || []

  return (
    <Card className="p-5">
      <CardHeader title="Chain of command" hindi="कमान श्रृंखला" />

      <dl className="mt-3 space-y-2 text-body-sm">
        <div className="flex justify-between gap-2">
          <dt className="text-ink-3">Signed in as</dt>
          <dd className="text-right text-ink">
            {user?.username} · <span className="text-ink-2">{user?.role}</span>
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-ink-3">Offence act</dt>
          <dd className="text-ink">{detail.details?.offence_act || 'Not decided'}</dd>
        </div>
      </dl>

      <div className="mt-4 flex flex-wrap gap-2">
        {mayAssign && (
          <Button size="sm" icon="person_add" onClick={() => setDialog('assign')}>Assign</Button>
        )}
        {mayAssign && (
          <Button variant="ghost" size="sm" icon="swap_horiz" onClick={() => setDialog('transfer')}>Transfer</Button>
        )}
        {mayVerify && (
          <Button variant="ghost" size="sm" icon="verified" loading={act.isPending} onClick={() => act.mutate({ kind: 'verify' })}>
            Verify report
          </Button>
        )}
      </div>
      {!mayAssign && (
        <p className="mt-3 text-body-sm text-ink-3">
          Assignment and transfer are station-head decisions. Your role ({user?.role}) may work the
          case and draft requisitions.
        </p>
      )}

      <h3 className="mt-6 text-label-ui uppercase text-ink-3">Audited history</h3>
      {audit.data?.status && (
        <p
          className={`mt-1 flex items-center gap-1 text-body-sm ${
            audit.data.status.intact ? 'text-risk-low-ink' : 'text-risk-high-ink'
          }`}
        >
          <Icon name={audit.data.status.intact ? 'verified_user' : 'gpp_maybe'} size={16} filled />
          {audit.data.status.summary}
        </p>
      )}
      <div className="mt-3 max-h-[320px] overflow-auto pr-1">
        {entries.length === 0 ? (
          <p className="text-body-sm text-ink-3">Nothing recorded for this case yet.</p>
        ) : (
          <Timeline
            label="Case audit trail"
            items={entries.map((entry) => ({
              id: entry.seq,
              time: formatDateTime(entry.at),
              tone: entry.action.includes('transfer') ? 'medium' : 'primary',
              title: entry.action.replace('.', ' · '),
              body: `${entry.actor_role} ${entry.actor_name}`,
            }))}
          />
        )}
      </div>

      <Modal
        open={Boolean(dialog)}
        onClose={() => setDialog(null)}
        title={dialog === 'assign' ? 'Assign this case' : 'Transfer to another unit'}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setDialog(null)}>Cancel</Button>
            <Button
              size="sm"
              loading={act.isPending}
              disabled={dialog === 'assign' ? !assignee.trim() : reason.trim().length < 5}
              onClick={() => act.mutate({ kind: dialog })}
            >
              Confirm
            </Button>
          </>
        }
      >
        {dialog === 'assign' ? (
          <div className="space-y-3">
            <label className="block text-body-sm font-semibold text-ink">
              Officer username
              <input
                value={assignee}
                onChange={(event) => setAssignee(event.target.value)}
                placeholder="e.g. sho.cyber"
                className="mt-1 h-10 w-full rounded-chip border border-line bg-white px-3 text-body-sm font-normal"
              />
            </label>
            <label className="block text-body-sm font-semibold text-ink">
              Offence act
              <select
                value={offenceAct}
                onChange={(event) => setOffenceAct(event.target.value)}
                className="mt-1 h-10 w-full rounded-chip border border-line bg-white px-3 text-body-sm"
              >
                {OFFENCE_ACTS.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
            </label>
            <p className="rounded-chip bg-canvas p-3 text-body-sm text-ink-2">
              An IT Act offence must go to an officer of Inspector rank or above (IT Act 2000,
              section 78). PARAKH refuses an assignment that would break this and says so.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <label className="block text-body-sm font-semibold text-ink">
              Receiving unit
              <select
                value={unitCode}
                onChange={(event) => setUnitCode(event.target.value)}
                className="mt-1 h-10 w-full rounded-chip border border-line bg-white px-3 text-body-sm"
              >
                {UNITS.map((item) => (
                  <option key={item.code} value={item.code}>{item.name}</option>
                ))}
              </select>
            </label>
            <label className="block text-body-sm font-semibold text-ink">
              Reason (recorded in the audit trail)
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                rows={3}
                className="mt-1 w-full rounded-chip border border-line bg-white p-3 text-body-sm font-normal"
                placeholder="e.g. Victim and suspect are both in Bharatpur."
              />
            </label>
          </div>
        )}
      </Modal>
    </Card>
  )
}
