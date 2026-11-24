import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, CardHeader, EmptyBlock, Icon, Modal, StateBlock, useToast } from '../../../design/ui'
import { deleteEvidence, listEvidence, readEvidence, saveEvidence, vaultIsAvailable } from '../../../lib/vault'
import { redactSensitiveText } from '../../../lib/redaction'

// Evidence locker (planversionalpha.md H.5; no Stitch screen). Items are
// encrypted with AES-GCM using a non-extractable key kept in this browser's
// IndexedDB (src/lib/vault.js). Nothing here is sent to the server.

const LOCKER = 'my-evidence'

const KINDS = {
  MESSAGE: ['Message', 'sms'],
  SCREENSHOT: ['Screenshot text', 'image'],
  VOICE_TRANSCRIPT: ['Voice note text', 'mic'],
  EMAIL: ['Email', 'mail'],
  URL: ['Link', 'link'],
  TRANSACTION_REFERENCE: ['Payment / UTR reference', 'receipt_long'],
}

function download(filename, text) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function AddEvidence({ onSaved }) {
  const [kind, setKind] = useState('TRANSACTION_REFERENCE')
  const [content, setContent] = useState('')
  const [note, setNote] = useState('')
  const toast = useToast()
  const save = useMutation({
    mutationFn: () => saveEvidence({ caseId: LOCKER, kind, content, note }),
    onSuccess: () => {
      setContent('')
      setNote('')
      toast('Saved and encrypted on this device.', 'success')
      onSaved()
    },
    onError: (error) => toast(error.message, 'error'),
  })
  const field = 'w-full rounded-chip border-[1.5px] border-line bg-white p-3 text-body-md outline-none focus:border-primary'
  return (
    <Card className="p-5">
      <CardHeader title="Add evidence" hindi="सबूत जोड़ें" />
      <form
        className="mt-3 space-y-3"
        onSubmit={(event) => {
          event.preventDefault()
          if (content.trim()) save.mutate()
        }}
      >
        <label className="block text-body-sm font-semibold text-ink">
          Type
          <select value={kind} onChange={(event) => setKind(event.target.value)} className={`${field} mt-1 h-11 py-0`}>
            {Object.entries(KINDS).map(([value, [text]]) => <option key={value} value={value}>{text}</option>)}
          </select>
        </label>
        <label className="block text-body-sm font-semibold text-ink">
          Details
          <textarea value={content} onChange={(event) => setContent(event.target.value)} rows={4} placeholder="Paste the message, UTR number, UPI ID paid to, amount and time…" className={`${field} mt-1 resize-y font-normal`} />
        </label>
        <label className="block text-body-sm font-semibold text-ink">
          Note (optional)
          <input value={note} onChange={(event) => setNote(event.target.value)} maxLength={280} placeholder="e.g. Paid at 4:10 PM from PhonePe" className={`${field} mt-1 font-normal`} />
        </label>
        <Button type="submit" icon="lock" loading={save.isPending} disabled={!content.trim()}>Save encrypted</Button>
      </form>
    </Card>
  )
}

export function EvidencePage() {
  const client = useQueryClient()
  const toast = useToast()
  const [viewing, setViewing] = useState(null)
  const available = useQuery({ queryKey: ['vault-available'], queryFn: vaultIsAvailable, staleTime: Infinity })
  const items = useQuery({ queryKey: ['vault', LOCKER], queryFn: () => listEvidence(LOCKER), enabled: available.data === true })
  const refresh = () => client.invalidateQueries({ queryKey: ['vault', LOCKER] })

  async function open(item) {
    const all = await readEvidence(LOCKER)
    setViewing(all.find((entry) => entry.id === item.id) || null)
  }

  async function exportAll(redacted) {
    const all = await readEvidence(LOCKER)
    const text = all
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt))
      .map((entry, index) => {
        const body = redacted ? redactSensitiveText(entry.content) : entry.content
        return `#${index + 1} · ${KINDS[entry.kind]?.[0] || entry.kind} · saved ${new Date(entry.createdAt).toLocaleString('en-IN')}\n${entry.note ? `Note: ${entry.note}\n` : ''}${body}\n`
      })
      .join('\n----------------------------------------\n\n')
    const header = `PARAKH evidence locker export (${redacted ? 'redacted copy for sharing' : 'full copy'})\nExported ${new Date().toLocaleString('en-IN')}\nThis is a personal record kept by the citizen, not a police document.\n\n`
    download(`parakh-evidence-${redacted ? 'redacted' : 'full'}.txt`, header + text)
  }

  const remove = useMutation({
    mutationFn: (id) => deleteEvidence(id),
    onSuccess: () => {
      toast('Deleted from this device.', 'info')
      setViewing(null)
      refresh()
    },
  })

  return (
    <div className="mx-auto max-w-[1180px] px-4 py-8 md:px-8">
      <h1 className="text-headline-lg-mobile md:text-headline-lg">
        Evidence locker <span className="hi block text-accent-strong md:inline" lang="hi">/ सबूत तिजोरी</span>
      </h1>
      <p className="mt-1 max-w-3xl text-body-md text-ink-2">
        Keep messages, links and payment references safe for your complaint. Everything is encrypted and stays in this browser on this device — it is not uploaded. Clearing browser data deletes it.
      </p>

      {available.data === false ? (
        <Card className="mt-6">
          <EmptyBlock icon="lock_open" title="This browser cannot store encrypted evidence">
            Private or very old browsers block secure storage. Save screenshots in your phone gallery instead and note the UTR number on paper.
          </EmptyBlock>
        </Card>
      ) : (
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_380px]">
          <Card className="p-5">
            <CardHeader
              title="Saved on this device"
              hindi="इस डिवाइस पर सहेजे गए"
              action={
                items.data?.length ? (
                  <div className="flex flex-wrap gap-2">
                    <Button variant="ghost" size="sm" icon="download" onClick={() => exportAll(true)}>Redacted copy</Button>
                    <Button variant="ghost" size="sm" icon="download" onClick={() => exportAll(false)}>Full copy</Button>
                  </div>
                ) : null
              }
            />
            <div className="mt-3">
              <StateBlock
                query={items}
                isEmpty={(data) => !data.length}
                empty={
                  <EmptyBlock icon="inventory_2" title="Nothing saved yet">
                    Save a result from the verdict screen, or add a payment reference here.
                  </EmptyBlock>
                }
              >
                {(data) => (
                  <ul className="divide-y divide-line-soft">
                    {data.map((item) => {
                      const [kindLabel, icon] = KINDS[item.kind] || [item.kind, 'description']
                      return (
                        <li key={item.id} className="flex items-center gap-3 py-3">
                          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-primary-tint text-primary"><Icon name={icon} size={20} /></span>
                          <div className="min-w-0 flex-1">
                            <p className="text-body-md font-semibold text-ink">{kindLabel}</p>
                            <p className="truncate text-body-sm text-ink-2">{item.note || 'No note'}</p>
                            <p className="text-body-sm text-ink-3 tnum">{new Date(item.createdAt).toLocaleString('en-IN')}</p>
                          </div>
                          <Button variant="ghost" size="sm" icon="visibility" onClick={() => open(item)}>View</Button>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </StateBlock>
            </div>
          </Card>
          <div className="space-y-4">
            <AddEvidence onSaved={refresh} />
            <div className="rounded-card bg-sand p-4 text-body-sm text-ink-2">
              <p className="font-semibold text-ink">For your 1930 / cybercrime.gov.in complaint, keep:</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5">
                <li>The transaction ID / UTR number, amount, date and time</li>
                <li>The UPI ID, account or number you paid to</li>
                <li>Screenshots of the chat, call log and payment</li>
                <li>Any link or app name the fraudster sent</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      <Modal
        open={Boolean(viewing)}
        onClose={() => setViewing(null)}
        title={viewing ? KINDS[viewing.kind]?.[0] || viewing.kind : ''}
        footer={
          viewing && (
            <>
              <Button variant="danger" size="sm" icon="delete" loading={remove.isPending} onClick={() => remove.mutate(viewing.id)}>Delete</Button>
              <Button variant="ghost" size="sm" onClick={() => setViewing(null)}>Close</Button>
            </>
          )
        }
      >
        {viewing && (
          <div className="space-y-2">
            {viewing.note && <p className="text-body-sm text-ink-2">Note: {viewing.note}</p>}
            <p className="max-h-[50vh] overflow-auto whitespace-pre-wrap break-words rounded-chip bg-canvas p-3 font-mono text-body-sm text-ink">{viewing.content}</p>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default EvidencePage
