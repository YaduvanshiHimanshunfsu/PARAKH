import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button, ButtonLink, Card, ConsentCheckbox, Icon, RiskBadge, Segmented, useToast } from '../../../design/ui'
import { citizenApi } from '../../../lib/api'
import { saveEvidence } from '../../../lib/vault'
import { EXPOSURE, SAFE_ACTION, SAFETY_DECISION, hindiLabel, label } from '../../../content/labels'
import { explainPayloadFlags } from './normalise'

const selectClass = 'h-11 w-full rounded-chip border-[1.5px] border-line bg-white px-3 text-body-md outline-none focus:border-primary'

export function ExposurePicker({ value, onChange }) {
  return (
    <Card className="p-5">
      <label htmlFor="exposure" className="text-title-md text-ink">
        What have you done so far? <span className="hi block text-body-sm font-normal text-ink-2" lang="hi">आपने अब तक क्या किया है?</span>
      </label>
      <select id="exposure" value={value} onChange={(event) => onChange(event.target.value)} className={`${selectClass} mt-2`}>
        {Object.keys(EXPOSURE).map((key) => (
          <option key={key} value={key}>
            {label(EXPOSURE, key)} · {hindiLabel(EXPOSURE, key)}
          </option>
        ))}
      </select>
      {value !== 'RECEIVED_ONLY' && (
        <ButtonLink
          to={`/rescue?exposure=${value}`}
          variant="danger"
          block
          icon="emergency"
          className="mt-3"
        >
          Open my rescue plan
        </ButtonLink>
      )}
    </Card>
  )
}

export function ExplainSimply({ model, exposure }) {
  const [lang, setLang] = useState('simple')
  const explain = useMutation({
    mutationFn: () =>
      citizenApi.explainSimply({
        verdict: model.verdict,
        scam_category: model.category || 'UNKNOWN',
        red_flags: explainPayloadFlags(model.redFlags),
        exposure_state: exposure,
      }),
  })
  const data = explain.data
  return (
    <Card className="p-5">
      <h2 className="flex items-center gap-2 text-title-md text-ink">
        <Icon name="record_voice_over" className="text-primary" /> Explain it simply
      </h2>
      <p className="hi text-body-sm text-ink-2" lang="hi">आसान भाषा में समझें — बड़ों को बताने के लिए</p>
      {!data ? (
        <Button variant="ghost" icon="lightbulb" className="mt-3" loading={explain.isPending} onClick={() => explain.mutate()}>
          Explain
        </Button>
      ) : (
        <div className="mt-3 space-y-3">
          <Segmented
            label="Explanation language"
            size="sm"
            value={lang}
            onChange={setLang}
            options={[
              { value: 'simple', label: 'English' },
              { value: 'hindi', label: 'हिंदी' },
              { value: 'hinglish', label: 'Hinglish' },
            ]}
          />
          <p className={`text-body-md text-ink ${lang === 'hindi' ? 'hi' : ''}`} lang={lang === 'hindi' ? 'hi' : undefined}>
            {lang === 'hindi' ? data.hindi_explanation : lang === 'hinglish' ? data.hinglish_explanation : data.simple_explanation}
          </p>
          <p className="text-body-sm text-ink-2">
            <span className="font-semibold text-ink">Why it is risky: </span>
            {data.why_risky}
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-chip bg-risk-low-bg p-3">
              <p className="text-label-ui uppercase text-risk-low-ink">Do</p>
              <ul className="mt-1 space-y-1 text-body-sm text-ink">
                {data.do_steps.map((step) => <li key={step}>✓ {step}</li>)}
              </ul>
            </div>
            <div className="rounded-chip bg-risk-high-bg p-3">
              <p className="text-label-ui uppercase text-risk-high-ink">Don’t</p>
              <ul className="mt-1 space-y-1 text-body-sm text-ink">
                {data.dont_steps.map((step) => <li key={step}>✕ {step}</li>)}
              </ul>
            </div>
          </div>
        </div>
      )}
      {explain.isError && <p role="alert" className="mt-2 text-body-sm text-risk-high-ink">{explain.error.message}</p>}
    </Card>
  )
}

export function SafeNextStep({ model, exposure }) {
  const [action, setAction] = useState('')
  const step = useMutation({
    mutationFn: (chosen) =>
      citizenApi.safeNextStep({
        action: chosen,
        verdict: model.verdict,
        scam_category: model.category || 'UNKNOWN',
        exposure_state: exposure,
      }),
  })
  const data = step.data
  const decision = data ? SAFETY_DECISION[data.decision] : null
  return (
    <Card className="p-5">
      <h2 className="flex items-center gap-2 text-title-md text-ink">
        <Icon name="front_hand" className="text-primary" /> About to do something?
      </h2>
      <p className="hi text-body-sm text-ink-2" lang="hi">कुछ करने से पहले पूछें</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {Object.keys(SAFE_ACTION).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => {
              setAction(key)
              step.mutate(key)
            }}
            aria-pressed={action === key}
            className={`inline-flex items-center gap-1 rounded-chip border px-2.5 py-1.5 text-body-sm font-semibold transition-colors ${
              action === key ? 'border-primary bg-primary text-white' : 'border-line bg-white text-ink-2 hover:border-primary hover:text-primary'
            }`}
          >
            <Icon name={SAFE_ACTION[key][2]} size={16} /> {label(SAFE_ACTION, key)}
          </button>
        ))}
      </div>
      {step.isPending && <p className="mt-3 text-body-sm text-ink-2">Checking…</p>}
      {data && (
        <div className="mt-4 rounded-chip border border-line p-4" aria-live="polite">
          <RiskBadge level={decision?.level || 'UNKNOWN'} />
          <p className="mt-2 text-title-md text-ink">{data.title}</p>
          <p className="mt-1 text-body-md text-ink-2">{data.simple_explanation}</p>
          <p className="hi mt-1 text-body-sm text-ink-2" lang="hi">{data.hindi_explanation}</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-body-sm text-ink">
            {data.steps.map((item) => <li key={item}>{item}</li>)}
          </ol>
        </div>
      )}
      {step.isError && <p role="alert" className="mt-2 text-body-sm text-risk-high-ink">{step.error.message}</p>}
    </Card>
  )
}

export function ReportToPolice({ model }) {
  const [consent, setConsent] = useState(false)
  const [note, setNote] = useState('')
  const report = useMutation({
    mutationFn: () =>
      citizenApi.reportToPolice({
        artifact_type: model.report.artifact_type,
        content: model.report.content,
        reporter_note: note.trim() || null,
        consent: true,
      }),
  })
  if (!model.report) return null
  const done = report.data
  return (
    <Card className="p-5">
      <h2 className="flex items-center gap-2 text-title-md text-ink">
        <Icon name="local_police" className="text-primary" /> Send to police for review
      </h2>
      <p className="hi text-body-sm text-ink-2" lang="hi">पुलिस को समीक्षा के लिए भेजें</p>
      {done ? (
        <div className="mt-3 rounded-chip bg-risk-low-bg p-4" aria-live="polite">
          <p className="text-label-ui uppercase text-risk-low-ink">Sent</p>
          <p className="mt-1 font-mono text-title-md text-ink">{done.reference}</p>
          <p className="mt-1 text-body-sm text-ink-2">{done.message}</p>
          <p className="mt-2 text-body-sm text-ink-2">
            This is not an FIR. To file a complaint, call <a href={`tel:${done.helpline}`} className="font-semibold text-primary">{done.helpline}</a> or use{' '}
            <a href={done.official_portal} target="_blank" rel="noreferrer" className="font-semibold text-primary underline">
              {done.official_portal.replace(/^https?:\/\//, '').replace(/\/$/, '')}
            </a>
            .
          </p>
          <ButtonLink to={`/status/${encodeURIComponent(done.reference)}`} variant="ghost" size="sm" icon="pending_actions" className="mt-3">
            Track this reference
          </ButtonLink>
        </div>
      ) : (
        <div className="mt-3 space-y-3">
          <p className="text-body-sm text-ink-2">
            Only what you checked is sent{model.report.artifact_type === 'URL' ? ' (the link)' : ''}. Officers review it and the identifiers help them link it to other cases. Your name and number are not asked for.
          </p>
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            maxLength={1000}
            rows={2}
            placeholder="Optional note: when and how you received it"
            aria-label="Optional note for police"
            className="w-full rounded-chip border-[1.5px] border-line bg-white p-3 text-body-sm outline-none focus:border-primary"
          />
          <ConsentCheckbox checked={consent} onChange={setConsent} hindi="मैं सहमत हूँ कि यह सामग्री पुलिस समीक्षा के लिए संग्रहीत की जाएगी।">
            I agree this content is stored for police review.
          </ConsentCheckbox>
          <Button icon="send" block disabled={!consent} loading={report.isPending} onClick={() => report.mutate()}>
            Send to police
          </Button>
          {report.isError && <p role="alert" className="text-body-sm text-risk-high-ink">{report.error.message}</p>}
        </div>
      )}
    </Card>
  )
}

export function SaveEvidence({ model }) {
  const toast = useToast()
  const [saved, setSaved] = useState(false)
  const save = useMutation({
    mutationFn: () =>
      saveEvidence({
        caseId: 'my-evidence',
        kind: model.evidenceKind,
        content: model.inputText || model.report?.content || '',
        note: `${model.title} · checked ${new Date(model.at).toLocaleString('en-IN')}`,
      }),
    onSuccess: () => {
      setSaved(true)
      toast('Saved, encrypted, on this device only.', 'success')
    },
    onError: (error) => toast(error.message, 'error'),
  })
  if (!model.inputText && !model.report) return null
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-card border border-line bg-card p-4">
      <Icon name="lock" className="text-primary" />
      <p className="min-w-0 flex-1 text-body-sm text-ink-2">Keep a copy as evidence. It is encrypted and stays on this device.</p>
      {saved ? (
        <ButtonLink to="/evidence" variant="ghost" size="sm" icon="folder_open">Open locker</ButtonLink>
      ) : (
        <Button variant="ghost" size="sm" icon="save" loading={save.isPending} onClick={() => save.mutate()}>Save</Button>
      )}
    </div>
  )
}
