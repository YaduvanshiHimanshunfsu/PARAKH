import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, CardHeader, EmptyBlock, FileDrop, Icon, IdentifierChip, Segmented, Stepper, StateBlock } from '../../design/ui'
import { officerApi } from '../../lib/api'
import { detectIdentifiers } from '../../lib/identifiers'
import { CaseLink, PageHeader } from './shared'

// Built from design/stitch/parakh_new_forensic_analysis_evidence_ingestion.
// Each type calls the real endpoint and opens a durable case:
//   MESSAGE / URL / EMAIL → POST /investigate/submit
//   WEBSITE               → POST /investigate/website/analyze (SSRF-guarded fetch)
//   APK                   → POST /investigate/apk/analyze (static parsing only)

const TYPES = [
  { value: 'MESSAGE', label: 'Message', icon: 'sms' },
  { value: 'URL', label: 'Link', icon: 'link' },
  { value: 'EMAIL', label: 'Email (.eml)', icon: 'mail' },
  { value: 'WEBSITE', label: 'Website', icon: 'language' },
  { value: 'APK', label: 'APK', icon: 'android' },
]

const HINT = {
  MESSAGE: 'SMS, WhatsApp or chat text exactly as received. Identifiers are extracted and linked to earlier cases.',
  URL: 'A link from a complaint. Checked for look-alike names, risky endings, short links, the certificate and earlier reports.',
  EMAIL: 'Paste the full raw email including headers so SPF, DKIM and DMARC can be checked.',
  WEBSITE: 'The page is fetched by the server (private addresses blocked, size-capped) and its content scored.',
  APK: 'Parsed statically: manifest, permissions, signing certificate, embedded strings. Never installed or run.',
}

const field = 'w-full rounded-chip border-[1.5px] border-line bg-white p-3 text-body-md outline-none focus:border-primary'

export function SubmitPage() {
  const [type, setType] = useState('MESSAGE')
  const [content, setContent] = useState('')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState(null)
  const [note, setNote] = useState('')
  const navigate = useNavigate()
  const client = useQueryClient()

  const recent = useQuery({ queryKey: ['cases', 'mine-recent'], queryFn: () => officerApi.searchCases({ mine: true, limit: 8 }) })

  const submit = useMutation({
    mutationFn: () => {
      const reporter_note = note.trim() || undefined
      if (type === 'APK') return officerApi.uploadApk(file, reporter_note)
      if (type === 'WEBSITE') return officerApi.analyseWebsite({ url: url.trim(), reporter_note })
      return officerApi.submit({ artifact_type: type, content: type === 'URL' ? url.trim() : content, reporter_note })
    },
    onSuccess: (created) => {
      client.invalidateQueries({ queryKey: ['cases'] })
      client.invalidateQueries({ queryKey: ['dashboard'] })
      navigate(`/investigate/case/${encodeURIComponent(created.case_id)}`)
    },
  })

  const usesUrl = type === 'URL' || type === 'WEBSITE'
  const ready = type === 'APK' ? Boolean(file) : usesUrl ? url.trim().length >= 4 : content.trim().length >= 3
  const chips = type === 'MESSAGE' || type === 'EMAIL' ? detectIdentifiers(content).slice(0, 12) : []

  return (
    <div>
      <PageHeader title="New analysis" hindi="नया विश्लेषण" eyebrow="Opens a case" />
      <div className="grid gap-6 xl:grid-cols-[1fr_380px] [&>*]:min-w-0">
        <Card className="p-5 md:p-6">
          <Segmented
            label="Artifact type"
            value={type}
            onChange={(value) => {
              setType(value)
              submit.reset()
            }}
            options={TYPES}
          />
          <p className="mt-3 text-body-sm text-ink-2">{HINT[type]}</p>

          {submit.isPending ? (
            <div className="mt-6" aria-live="polite">
              <Stepper
                label="Analysis progress"
                steps={[
                  { label: 'Received', status: 'done' },
                  { label: type === 'APK' ? 'Parse package' : type === 'WEBSITE' ? 'Fetch page' : 'Analyse', status: 'current' },
                  { label: 'Extract identifiers', status: 'current' },
                  { label: 'Link to cases', status: 'todo' },
                ]}
              />
            </div>
          ) : (
            <form
              className="mt-5 space-y-4"
              onSubmit={(event) => {
                event.preventDefault()
                if (ready) submit.mutate()
              }}
            >
              {type === 'APK' ? (
                <FileDrop accept=".apk,application/vnd.android.package-archive" icon="android" title={file ? file.name : 'Drop the .apk file'} hint="Parsed on the server; never installed or run" onFile={setFile} />
              ) : usesUrl ? (
                <label className="block text-body-sm font-semibold text-ink">
                  {type === 'WEBSITE' ? 'Website address' : 'Link'}
                  <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://…" className={`${field} mt-1 font-mono`} />
                </label>
              ) : (
                <label className="block text-body-sm font-semibold text-ink">
                  {type === 'EMAIL' ? 'Raw email (headers + body)' : 'Message text'}
                  <textarea value={content} onChange={(event) => setContent(event.target.value)} rows={type === 'EMAIL' ? 12 : 7} className={`${field} mt-1 resize-y ${type === 'EMAIL' ? 'font-mono text-body-sm' : ''}`} />
                </label>
              )}
              {chips.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {chips.map((chip) => <IdentifierChip key={`${chip.type}:${chip.value}`} type={chip.type} value={chip.value} copy={false} />)}
                </div>
              )}
              <label className="block text-body-sm font-semibold text-ink">
                Reporter / complaint note <span className="font-normal text-ink-3">(optional)</span>
                <input value={note} onChange={(event) => setNote(event.target.value)} maxLength={1000} placeholder="e.g. Walk-in complaint, PS Vaishali Nagar, 24 Nov" className={`${field} mt-1`} />
              </label>
              {submit.isError && (
                <p role="alert" className="flex items-start gap-2 rounded-chip bg-risk-high-bg p-3 text-body-sm text-risk-high-ink">
                  <Icon name="error" size={18} filled /> {submit.error.message}
                </p>
              )}
              <Button type="submit" size="lg" icon="biotech" disabled={!ready}>Analyse and open case</Button>
            </form>
          )}
        </Card>

        <Card className="p-5">
          <CardHeader title="My recent submissions" hindi="मेरे हाल के केस" />
          <div className="mt-3">
            <StateBlock query={recent} isEmpty={(data) => !data.cases.length} empty={<EmptyBlock icon="history" title="Nothing submitted yet" />}>
              {(data) => (
                <ul className="divide-y divide-line-soft">
                  {data.cases.map((item) => <li key={item.case_id}><CaseLink summary={item} compact /></li>)}
                </ul>
              )}
            </StateBlock>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default SubmitPage
